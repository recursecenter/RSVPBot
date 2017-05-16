# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import datetime
from time import mktime
import random
import urllib.parse

from pytimeparse.timeparse import timeparse
import parsedatetime

import calendar_events
import strings
import util
from zulip_users import ZulipUsers
from models import Event
import rc


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
  def __init__(self, events, *args):
    self.events = events
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

  def execute(self, events, *args, **kwargs):
    """execute() is just a convenience wrapper around __run()."""
    return self.run(events, *args, **kwargs)


class RSVPEventNeededCommand(RSVPCommand):
  """Base class for a command where an event needs to exist prior to execution."""
  def execute(self, events, *args, **kwargs):
    stream = kwargs.get('stream')
    subject = kwargs.get('subject')
    event = Event.query.filter(Event.stream == stream and Event.subject == subject).first()

    if event:
      event.refresh_from_api()
      return self.run(events, *args, **{**kwargs, "event": event})
    else:
      return RSVPCommandResponse(events, RSVPMessage('private', strings.ERROR_NOT_AN_EVENT, kwargs.get('sender_email')))


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

class RSVPInitCommand(RSVPCommand):
  regex = r'init (?P<rc_id_or_url>.+)'

  def run(self, events, *args, **kwargs):
    stream = kwargs.pop('stream')
    subject = kwargs.pop('subject')
    sender_email = kwargs.pop('sender_email')
    rc_id_or_url = kwargs.pop('rc_id_or_url')
    rc_event_id = extract_id(rc_id_or_url)

    if not rc_event_id:
      return RSVPCommandResponse(events, RSVPMessage('private', strings.ERROR_NO_EVENT_ID, sender_email))

    event = Event.query.filter(Event.recurse_id == rc_event_id).first()

    if event is None:
      event_dict = rc.get_event(rc_event_id)

      if event_dict is None:
        return RSVPCommandResponse(events, RSVPMessage('private', strings.ERROR_EVENT_NOT_FOUND.format(rc_id_or_url), sender_email))

      event = insert_event(event_dict)
    else:
      event.refresh_from_api()

    if event.already_initialized():
      return RSVPCommandResponse(events, RSVPMessage('stream', strings.ERROR_EVENT_ALREADY_INITIALIZED.format(event.zulip_link())))

    event.update(stream=stream, subject=subject)

    return RSVPCommandResponse(events, RSVPMessage('stream', strings.MSG_INIT_SUCCESSFUL))


class RSVPCreateCalendarEventCommand(RSVPEventNeededCommand):
  regex = r'add to calendar$'

  def run(self, events, *args, **kwargs):
    event = kwargs.pop('event')
    return RSVPCommandResponse(events, RSVPMessage('stream', strings.ERROR_GOOGLE_CALENDAR_NO_LONGER_USED.format(event.url)))


class RSVPHelpCommand(RSVPCommand):
  regex = r'help$'

  with open('README.md', 'r') as readme_file:
      readme_contents = readme_file.read()
      _, commands_table = readme_contents.split("## Commands\n")

  def run(self, events, *args, **kwargs):
    sender_email = kwargs.pop('sender_email')
    return RSVPCommandResponse(events, RSVPMessage('private', self.commands_table, sender_email))


class RSVPMoveCommand(RSVPEventNeededCommand):
  regex = r'move (?P<destination>.+)$'

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    sender_id = kwargs.pop('sender_id')
    event = kwargs.pop('event')
    destination = kwargs.pop('destination')
    success_msg = None

    # Check if the issuer of this command is the event's original creator.
    # Only she can modify the event.
    creator = event['creator']

    # check and make sure a valid Zulip stream/topic URL is passed
    if not destination:
      body = strings.ERROR_MISSING_MOVE_DESTINATION
    elif creator != sender_id:
      body = strings.ERROR_NOT_AUTHORIZED_TO_DELETE
    else:
      # split URL into components
      stream, topic = util.narrow_url_to_stream_topic(destination)

      if stream is None or topic is None:
        body = strings.ERROR_BAD_MOVE_DESTINATION % destination
      else:
        new_event_id = stream + "/" + topic

        if new_event_id in events:
          body = strings.ERROR_MOVE_ALREADY_AN_EVENT % new_event_id
        else:
          body = strings.MSG_EVENT_MOVED % (new_event_id, destination)

          old_event = events.pop(event_id)

          # need to make sure that there's no duplicate here!
          # also, ideally we'd make sure the stream/topic existed & create it if not.
          # AND send an 'init' notification to that new stream/toipic. Hm. what's the
          # best way to do that? Allow for a parameterized init? It's always a reply, not a push.
          # Can we return MULTIPLE messages instead of just one?

          old_event.update({'name': topic})

          events.update(
            {
              new_event_id: old_event
            }
          )

          success_msg = RSVPMessage('stream', strings.MSG_INIT_SUCCESSFUL, stream, topic)

    return RSVPCommandResponse(events, RSVPMessage('stream', body), success_msg)


class LimitReachedException(Exception):
  pass


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

  def generate_response(self, decision, event_id, funkify=False):
      response_string = self.responses.get(decision) % event_id
      if not funkify:
          return response_string
      if decision == 'yes':
        return random.choice(self.funky_yes_prefixes) + response_string
      elif decision == 'no':
        return response_string + random.choice(self.funky_no_postfixes)
      return response_string

  def confirm(self, event, event_id, sender_email, decision):
    # Temporary kludge to add a 'maybe' array to legacy events. Can be removed after
    # all currently logged events have passed.
    if ('maybe' not in event.keys()):
      event['maybe'] = []

    # If they're in a different response list, take them out of it.
    for response in self.responses.keys():
      # prevent duplicates if replying multiple times
      if (response == decision):
        # if they're already in that list, nothing to do
        if (sender_email not in event[response]):
          event[response].append(sender_email)
      # else, remove all instances of them from other response lists.
      elif sender_email in event[response]:
        event[response] = [value for value in event[response] if value != sender_email]
      calendar_event_id = event.get('calendar_event') and event['calendar_event']['id']
      if calendar_event_id:
        try:
          calendar_events.update_gcal_event(event, event_id)
        except calendar_events.KeyfilePathNotSpecifiedError:
          pass

    return event

  def attempt_confirm(self, event, event_id, sender_email, decision, limit):
    if decision == 'yes' and limit:
      available_seats = limit - len(event['yes'])
      # In this case, we need to do some extra checking for the attendance limit.
      if (available_seats - 1 < 0):
        raise LimitReachedException()

    return self.confirm(event, event_id, sender_email, decision)

  def run(self, events, *args, **kwargs):
    event_id = kwargs.pop('event_id')
    event = kwargs.pop('event')
    yes_decision = kwargs.pop('yes_decision')
    no_decision = kwargs.pop('no_decision')
    decision = 'yes' if yes_decision else ('no' if no_decision else 'maybe')
    sender_name = kwargs.pop('sender_full_name')
    sender_email = kwargs.pop('sender_email')

    limit = event['limit']

    try:
      event = self.attempt_confirm(event, event_id,  sender_email, decision, limit)

      # Update the events dict with the new event.
      events[event_id] = event
      # 1 in 10 chance of generating a funky response
      response = self.generate_response(decision, event_id, funkify=(random.random() < 0.1))
    except LimitReachedException:
      response = strings.ERROR_LIMIT_REACHED
    return RSVPCommandResponse(events, RSVPMessage('private', response, sender_email))


class RSVPPingCommand(RSVPEventNeededCommand):
  regex = r'^({key_word} ping)$|({key_word} ping (?P<message>.+))$'

  def __init__(self, prefix, *args, **kwargs):
    self.regex = self.regex.format(key_word=prefix)

  def get_users_dict(self):
    return ZulipUsers()

  def run(self, events, *args, **kwargs):
    users = self.get_users_dict()

    event = kwargs.pop('event')
    message = kwargs.get('message')

    body = "**Pinging all participants who RSVP'd!!**\n"

    for participant in event['yes']:
      body += "@**%s** " % users.convert_email_to_pingable_name(participant)

    for participant in event['maybe']:
      body += "@**%s** " % users.convert_email_to_pingable_name(participant)

    if message:
      body += ('\n' + message)

    return RSVPCommandResponse(events, RSVPMessage('stream', body))


class RSVPCreditsCommand(RSVPEventNeededCommand):
  regex = r'credits$'

  def run(self, events, *args, **kwargs):

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
      "James J. Porter (S'13)",
    ]

    testers = ["Nikki Bee (SP2'15)", "Anthony Burdi (SP1'15)", "Noella D'sa (SP2'15)", "Mudit Ameta (SP2'15)"]

    body = "The RSVPBot was created by @**Carlos Rey (SP2'15)**\nWith **contributions** from:\n\n"

    body += '\n '.join(contributors)

    body += "\n\n and invaluable test feedback from:\n\n"
    body += '\n '.join(testers)

    body += "\n\nThe code for **RSVPBot** is available at https://github.com/kokeshii/RSVPBot"

    return RSVPCommandResponse(events, RSVPMessage('private', body, sender_email))


class RSVPSummaryCommand(RSVPEventNeededCommand):
  regex = r'(summary$|status$)'

  def get_users_dict(self):
    return ZulipUsers()

  def run(self, events, *args, **kwargs):
    event = kwargs.pop('event')
    users = self.get_users_dict()

    summary_table = '**%s**' % (event['name'])
    summary_table += '\t|\t\n:---:|:---:\n'

    if event['description']:
        summary_table += '**What**|%s\n' % event['description']

    summary_table += '**When**|%s @ %s\n' % (event['date'], event['time'] or '(All day)')

    if event['duration']:
        summary_table += '**Duration**|%s\n' % datetime.timedelta(seconds=event['duration'])

    if event['place']:
        summary_table += '**Where**|%s\n' % event['place']

    if event['limit']:
        limit_str = '%d/%d spots left' % (event['limit'] - len(event['yes']), event['limit'])
        summary_table += '**Limit**|%s\n' % limit_str

    confirmation_table = 'YES ({}) |NO ({}) |MAYBE({}) \n:---:|:---:|:---:\n'

    confirmation_table = confirmation_table.format(len(event['yes']), len(event['no']), len(event['maybe']))

    row_list = map(None, event['yes'], event['no'], event['maybe'])

    for row in row_list:
      confirmation_table += '{}|{}|{}\n'.format(
        '' if row[0] is None else users.convert_email_to_pingable_name(row[0]),
        '' if row[1] is None else users.convert_email_to_pingable_name(row[1]),
        '' if row[2] is None else users.convert_email_to_pingable_name(row[2])
      )
    else:
      confirmation_table += '\t|\t'

    body = summary_table + '\n\n' + confirmation_table
    return RSVPCommandResponse(events, RSVPMessage('stream', body))


class RSVPFunctionalityMovedCommand(RSVPEventNeededCommand):
  def run(self, events, *args, **kwargs):
    return RSVPCommandResponse(events, RSVPMessage('stream', strings.ERROR_FUNCTIONALITY_MOVED.format(self.name, kwargs['event'].url)))

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
