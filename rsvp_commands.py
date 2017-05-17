# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import datetime
from time import mktime
import random
import urllib.parse

from pytimeparse.timeparse import timeparse
import parsedatetime

import strings
import util
from models import Event, Session
import rc
import zulip_util
import config


def zulip_names_from_participants(participants):
  zulip_ids = [p['person']['zulip_id'] for p in participants]
  return zulip_util.get_names(zulip_ids)

def extract_id(id_or_url):
  try:
    return int(id_or_url)
  except ValueError:
    pass

  uri = urllib.parse.urlparse(id_or_url)

  if uri.scheme not in ['http', 'https']:
    return None

  id_component = uri.path.split('/')[-1]
  id_match = re.search(r"\d+", id_component)

  if id_match:
    return int(id_match[0])
  else:
    return None


class RSVPMessage(object):
  """Class that represents a response from an RSVPCommand.

  Every call to an RSVPCommand instance's execute() method is expected to return an instance
  of this class.
  """
  def __init__(self, msg_type, body, to=None, subject=None):
    self.type = msg_type
    self.body = body
    self.to = to
    self.subject = subject

  def __getitem__(self, attr):
    self.__dict__[attr]

  def __str__(self):
    attr_string = ""
    for key in dir(self):
      attr_string += key + ":" + str(getattr(self, key)) + ", "
    return attr_string


class RSVPCommandResponse(object):
  def __init__(self, *args):
    self.messages = []
    for arg in args:
      if isinstance(arg, RSVPMessage):
        self.messages.append(arg)


class RSVPCommand(object):
  """Base class for an RSVPCommand."""
  regex = None

  def __init__(self, prefix, *args, **kwargs):
    # prefix is the command start the bot listens to, typically 'rsvp'
    self.prefix = r'^' + prefix + r' '
    self.regex = self.prefix + self.regex

  def match(self, input_str):
    return re.match(self.regex, input_str, flags=re.DOTALL | re.I)

  def execute(self, *args, **kwargs):
    """execute() is just a convenience wrapper around __run()."""
    return self.run(*args, **kwargs)


class RSVPEventNeededCommand(RSVPCommand):
  """Base class for a command where an event needs to exist prior to execution."""
  include_participants = False

  def execute(self, *args, **kwargs):
    stream = kwargs.get('stream')
    subject = kwargs.get('subject')
    event = Session.query(Event).filter(Event.stream == stream).filter(Event.subject == subject).first()

    if event:
      api_response = event.refresh_from_api(self.include_participants)
      return self.run(*args, **{**kwargs, "event": event, "api_response": api_response})
    else:
      return RSVPCommandResponse(RSVPMessage('private', strings.ERROR_NOT_AN_EVENT, kwargs.get('sender_email')))


class RSVPInitCommand(RSVPCommand):
  regex = r'init (?P<rc_id_or_url>.+)'

  def run(self, *args, **kwargs):
    stream = kwargs.pop('stream')
    subject = kwargs.pop('subject')
    sender_email = kwargs.pop('sender_email')
    rc_id_or_url = kwargs.pop('rc_id_or_url')
    rc_event_id = extract_id(rc_id_or_url)

    if stream == config.rsvpbot_stream and subject == config.rsvpbot_announce_subject:
      return RSVPCommandResponse(RSVPMessage('stream', strings.ERROR_CANNOT_INIT_IN_ANNOUNCE_THREAD))

    if Session.query(Event).filter(Event.stream == stream).filter(Event.subject == subject).count() > 0:
      return RSVPCommandResponse(RSVPMessage('private', strings.ERROR_ALREADY_AN_EVENT, sender_email))

    if not rc_event_id:
      return RSVPCommandResponse(RSVPMessage('private', strings.ERROR_NO_EVENT_ID, sender_email))

    event = Session.query(Event).filter(Event.recurse_id == rc_event_id).first()

    if event is None:
      event_dict = rc.get_event(rc_event_id)

      if event_dict is None:
        return RSVPCommandResponse(RSVPMessage('private', strings.ERROR_EVENT_NOT_FOUND.format(rc_id_or_url), sender_email))

      event = insert_event(event_dict)
    else:
      event.refresh_from_api()

    if event.already_initialized():
      return RSVPCommandResponse(RSVPMessage('stream', strings.ERROR_EVENT_ALREADY_INITIALIZED.format(event.zulip_link())))

    event.update(stream=stream, subject=subject)

    return RSVPCommandResponse(RSVPMessage('stream', strings.MSG_INIT_SUCCESSFUL.format(event.title, event.url)))


class RSVPHelpCommand(RSVPCommand):
  regex = r'help$'

  with open('README.md', 'r') as readme_file:
      readme_contents = readme_file.read()
      _, commands_table = readme_contents.split("## Commands\n")

  def run(self,  *args, **kwargs):
    sender_email = kwargs.pop('sender_email')
    return RSVPCommandResponse(RSVPMessage('private', self.commands_table, sender_email))


class RSVPMoveCommand(RSVPEventNeededCommand):
  regex = r'move (?P<destination>.+)$'

  def run(self, *args, **kwargs):
    sender_id = kwargs.pop('sender_id')
    event = kwargs.pop('event')
    destination = kwargs.pop('destination').strip()
    success_msg = None

    if not destination:
      body = strings.ERROR_MISSING_MOVE_DESTINATION
    else:
      stream, subject = util.narrow_url_to_stream_topic(destination)
      destination_name = "#{} > {}".format(stream, subject)

      if stream is None or subject is None:
        body = strings.ERROR_BAD_MOVE_DESTINATION % destination
      elif Session.query(Event).filter(Event.stream == stream).filter(Event.subject == subject).count() > 0:
        body = strings.ERROR_MOVE_ALREADY_AN_EVENT % destination_name
      else:
        event.update(stream=stream, subject=subject)
        body = strings.MSG_EVENT_MOVED % (destination_name, destination)
        success_msg = RSVPMessage('stream', strings.MSG_INIT_SUCCESSFUL.format(event.title, event.url), stream, subject)

    return RSVPCommandResponse(RSVPMessage('stream', body), success_msg)


class RSVPConfirmCommand(RSVPEventNeededCommand):
  yes_answers = (
    "ye(s+?)",
    "yea(h+?)",
    "in",
    "yep",
    "ya(s+?)",
    ":thumbs_?up:",
    "y",
    ":\+1:"
  )
  no_answers = (
    "n(o+?)",
    "out",
    "nope",
    "na(h+?)",
    ":thumbs_?down:",
    "n",
    ":-1:"
  )

  regex_yes = '(?P<yes_decision>%s)' % format('|'.join(yes_answers))
  regex_no = '(?P<no_decision>%s)' % format('|'.join(no_answers))
  regex_maybe = '(?P<maybe_decision>maybe)'

  # We're using a negative lookahead/lookbehind to make sure that whatever is
  # matched is a word on its own, i.e. we want to match "yes" but not
  # "yesterday". We can't use simple word boundaries here ("\b") if we want to
  # support emojis like :thumbsup: because ':' is not a word character.
  regex = r'.*?(?<!\w)({yes}|{no}|{maybe})(?!\w)'.format(
    yes=regex_yes,
    no=regex_no,
    maybe=regex_maybe)

  responses = {
    "yes": "**You** are attending **%s**!",
    "no": "You are **not** attending **%s**!",
    "maybe": "You **might** be attending **%s**. It's complicated.",
  }

  check_event = "You're still RSVP'd, but you should [check the event]({}) to make sure you can attend."

  funky_yes_prefixes = [
    "GET EXCITED!! ",
    "AWWW YISS!! ",
    "YASSSSS HENNY! ",
    "OMG OMG OMG ",
    "HYPE HYPE HYPE HYPE HYPE ",
    "WOW THIS IS AWESOME: ",
    "YEAAAAAAHHH!!!! :tada: ",
  ]

  funky_no_postfixes = [
    " :confounded:",
    " Bummer!",
    " Oh no!!",
  ]

  def generate_response(self, decision, event, funkify=False):
    response_string = self.responses.get(decision) % event.title
    if not funkify:
      return response_string
    if decision == 'yes':
      return random.choice(self.funky_yes_prefixes) + response_string
    elif decision == 'no':
      return response_string + random.choice(self.funky_no_postfixes)
    return response_string

  def get_decision(self, yes_decision, no_decision, maybe_decision, **kwargs):
    if yes_decision:
      return 'yes'
    elif no_decision:
      return 'no'
    else:
      return 'maybe'

  def run(self, *args, **kwargs):
    event = kwargs['event']
    sender_id = kwargs['sender_id']
    decision = self.get_decision(**kwargs)
    funkify = random.random() < 0.1

    if decision == 'maybe':
      return RSVPCommandResponse(RSVPMessage('private', strings.ERROR_RSVP_MAYBE_NOT_SUPPORTED, kwargs['sender_email']))
    elif decision == 'yes':
      result = rc.join(event.recurse_id, sender_id)

      if result['joined']:
        if result['over_capacity'] and result['past_deadline']:
          response = "This event is over capacity and past the RSVP deadline! " + self.check_event.format(event.url)
        elif result['over_capacity']:
          response = "This event is over capacity! " + self.check_event.format(event.url)
        elif result['past_deadline']:
          response = "This event is past the RSVP deadline! " + self.check_event.format(event.url)
        else:
          response = self.generate_response('yes', event, funkify=funkify)
      else:
        if result['event_archived']:
          response = "Oops! This event has been canceled, so you weren't able to RSVP."
        elif result['rsvps_disabled']:
          response = "Oops! RSVPs have been disabled for this event. You may be able to learn more [on the calendar]({}).".format(event.url)
        else:
          response = "Oops! Something went wrong. Here are the errors:\n\n" + "\n".join(result['errors'])
    else:
      rc.leave(event.recurse_id, sender_id)
      response = self.generate_response('no', event, funkify=funkify)

    return RSVPCommandResponse(RSVPMessage('private', response, kwargs['sender_email']))


class RSVPPingCommand(RSVPEventNeededCommand):
  regex = r'^({key_word} ping)$|({key_word} ping (?P<message>.+))$'
  include_participants = True

  def __init__(self, prefix, *args, **kwargs):
    self.regex = self.regex.format(key_word=prefix)

  def run(self, *args, **kwargs):
    event = kwargs['event']
    api_response = kwargs['api_response']
    message = kwargs.get('message')

    if api_response['anonymize_participants']:
      body = "Oops! Attendees are hidden for this event"
    else:
      body = "**Pinging all participants who RSVP'd!!**\n"

      for name in zulip_names_from_participants(api_response['participants']):
        body += "@**%s** " % name

      if message:
        body += '\n' + message

    return RSVPCommandResponse(RSVPMessage('stream', body))


class RSVPCreditsCommand(RSVPCommand):
  regex = r'credits$'

  def run(self, *args, **kwargs):
    sender_email = kwargs.pop('sender_email')

    contributors = [
      "Mudit Ameta (SP2'15)",
      "Diego Berrocal (F2'15)",
      "Shad William Hopson (F1'15)",
      "Tom Murphy (F2'15)",
      "Miriam Shiffman (F2'15)",
      "Anjana Sofia Vakil (F2'15)",
      "Steven McCarthy (SP2'15)",
      "Kara McNair (F2'15)",
      "Pris Nasrat (SP2'16)",
      "Benjamin Gilbert (F2'15)",
      "Andrew Drozdov (SP1'15)",
      "Alex Wilson (S1'16)",
      "Jérémie Jost (S1'16)",
      "Amulya Reddy (S1'16)",
      "James J. Porter (Faculty, S'13)",
      "Zach Allaun (Faculty, S'12)",
      "David Albert (Faculty)",
    ]

    testers = ["Nikki Bee (SP2'15)", "Anthony Burdi (SP1'15)", "Noella D'sa (SP2'15)", "Mudit Ameta (SP2'15)"]

    body = "The RSVPBot was created by @**Carlos Rey (SP2'15)**\nWith **contributions** from:\n\n"

    body += '\n '.join(contributors)

    body += "\n\n and invaluable test feedback from:\n\n"
    body += '\n '.join(testers)

    body += "\n\nThe code for this fork of **RSVPBot** can be found at https://github.com/recursecenter/RSVPBot.\n\nThe code for the original **RSVPBot** can be found at https://github.com/kokeshii/RSVPBot."

    return RSVPCommandResponse(RSVPMessage('private', body, sender_email))


class RSVPSummaryCommand(RSVPEventNeededCommand):
  regex = r'(summary$|status$)'
  include_participants = True

  def run(self, *args, **kwargs):
    event = kwargs['event']
    api_response = kwargs['api_response']
    participants = api_response.get('participants')

    summary_table = '**%s**' % (event.title)
    summary_table += '\t|\t\n:---:|:---:\n'

    if api_response.get('description'):
      summary_table += '**What**|%s\n' % api_response['description']

    summary_table += '**When**|%s\n' % event.timestamp()

    if 'location' in api_response:
      location = api_response['location']
      location_components = filter(lambda x: x, [location.get('name'), location.get('address'), location.get('city')])
      summary_table += '**Where**|%s\n' % ', '.join(location_components)

    if api_response.get('rsvp_capacity'):
      limit_str = '%d/%d spots left' % (api_response['rsvp_capacity'] - api_response['participant_count'], api_response['rsvp_capacity'])
      summary_table += '**Limit**|%s\n' % limit_str

    if api_response.get('rsvp_deadline'):
      deadline = models.parse_time(api_response, 'rsvp_deadline')
      time = deadline.strftime("%-I:%M%p").lower()
      zone = deadline.tzinfo.tzname(deadline)
      date = deadline.strftime("%A, %b %-d, %Y")
      summary_table += '**Deadline**|%s %s, %s\n' % (time, zone, date)

    if api_response['anonymize_participants']:
      attendees = "Participants are hidden for this event."
    else:
      attendees = '**Attendees**\n'
      for name in zulip_names_from_participants(api_response['participants']):
        attendees += name + '\n'

    body = summary_table + '\n\n' + attendees
    return RSVPCommandResponse(RSVPMessage('stream', body))



class RSVPCreateCalendarEventCommand(RSVPEventNeededCommand):
  regex = r'add to calendar$'

  def run(self, *args, **kwargs):
    event = kwargs.pop('event')
    return RSVPCommandResponse(RSVPMessage('stream', strings.ERROR_GOOGLE_CALENDAR_NO_LONGER_USED.format(event.url)))

class RSVPFunctionalityMovedCommand(RSVPEventNeededCommand):
  def run(self, *args, **kwargs):
    return RSVPCommandResponse(RSVPMessage('stream', strings.ERROR_FUNCTIONALITY_MOVED.format(self.name, kwargs['event'].url)))

class RSVPSetLimitCommand(RSVPFunctionalityMovedCommand):
  regex = r'set limit (?P<limit>\d+)$'
  name = 'set limit'

class RSVPSetDateCommand(RSVPFunctionalityMovedCommand):
  regex = r'set date (?P<date>.*)$'
  name = 'set date'

class RSVPSetTimeCommand(RSVPFunctionalityMovedCommand):
  regex = r'set time (?P<hours>\d{1,2})\:(?P<minutes>\d{1,2})$'
  name = 'set time'

class RSVPSetTimeAllDayCommand(RSVPFunctionalityMovedCommand):
  regex = r'set time allday$'
  name = 'set time'

class RSVPSetLocationCommand(RSVPFunctionalityMovedCommand):
  regex = r'set (?P<attribute>location) (?P<value>.+)$'
  name = 'set location'

class RSVPSetPlaceCommand(RSVPFunctionalityMovedCommand):
  regex = r'set (?P<attribute>place) (?P<value>.+)$'
  name = 'set place'

class RSVPSetDescriptionCommand(RSVPFunctionalityMovedCommand):
  regex = r'set (?P<attribute>description) (?P<value>.+)$'
  name = 'set description'

class RSVPCancelCommand(RSVPFunctionalityMovedCommand):
  regex = r'cancel$'
  name = "cancel"

class RSVPSetDurationCommand(RSVPFunctionalityMovedCommand):
  regex = r'set duration (?P<duration>.+)$'
  name = 'set duration'
