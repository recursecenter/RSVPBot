from __future__ import with_statement
import re
import json
import time
import datetime

ERROR_NOT_AN_EVENT = "This thread is not an RSVPBot event!. Type `rsvp init` to make it into an event."
ERROR_NOT_AUTHORIZED_TO_DELETE = "Oops! You cannot cancel this event! You're not this event's original creator! Only he can cancel it."
ERROR_ALREADY_AN_EVENT = "Oops! This thread is already an RSVPBot event!"
ERROR_TIME_NOT_VALID = "Oops! **%02d:%02d** is not a valid time!"
ERROR_DATE_NOT_VALID = "Oops! **%02d/%02d/%04d** is not a valid date in the **future**!"
ERROR_INVALID_COMMAND = "`rsvp set %s` is not a valid RSVPBot command! Type `rsvp help` for the correct syntax."

MSG_DATE_SET = 'The date for this event has been set to **%02d/%02d/%04d**!\n`rsvp help` for more options.'
MSG_TIME_SET = 'The time for this event has been set to **%02d:%02d**!.\n`rsvp help` for more options.'

class RSVP(object):

  def __init__(self):
    self.filename = 'events.json'

    with open(self.filename, "r") as f:
      try:
        self.events = json.load(f)
      except ValueError:
        self.events = {}

  def commit_events(self):
    with open(self.filename, 'w+') as f:
      json.dump(self.events, f)

  def __exit__(self, type, value, traceback):
    self.commit_events()

  def get_this_event(self, message):
    event_id = self.event_id(message)
    return self.events.get(event_id)

  def process_message(self, message):
    return self.route(message)

  def route(self, message):

    content = message['content']
    content = self.normalize_whitespace(content)
    body = None

    if content.startswith('rsvp'):

      if re.match(r'^rsvp init$', content):
        return self.cmd_rsvp_init(message)
      elif re.match(r'^rsvp help$', content):
        return self.cmd_rsvp_help(message)
      elif re.match(r'^rsvp cancel$', content):
        return self.cmd_rsvp_cancel(message)
      elif re.match(r'^rsvp yes$', content):
        return self.cmd_rsvp_confirm(message, 'yes')
      elif re.match(r'^rsvp no$', content):
        return self.cmd_rsvp_confirm(message, 'no')
      elif re.match(r'^rsvp summary$', content):
        return self.cmd_rsvp_summary(message)
      elif re.match(r'^rsvp set', content):
        """
        The command doesn't match the 'simple' commands, time to match against composite commands.
        """
        content = content.replace('rsvp set ', '')
        match = re.match(r'^time (?P<hours>\d{1,2})\:(?P<minutes>\d{1,2})$', content)

        if match:
          return self.cmd_rsvp_set_time(
            message,
            hours=match.group('hours'),
            minutes=match.group('minutes')
          )

        match = re.match(r'^date (?P<month>\d+)/(?P<day>\d+)/(?P<year>\d{4})$', content)

        if match:
          return self.cmd_rsvp_set_date(
            message,
            day=match.group('day'),
            month=match.group('month'),
            year=match.group('year')
          )
        # ...
        return ERROR_INVALID_COMMAND % (content)

    return None
    
  def create_message_from_message(self, message, body):
    if body:
      return {
        'subject': message['subject'],
        'display_recipient': message['display_recipient'],
        'body': body
      }


  def event_id(self, message):
    return u'{}/{}'.format(message['display_recipient'], message['subject'])


  def cmd_rsvp_set_date(self, message, day='1', month='1', year='2000'):
    event = self.get_this_event(message)
    event_id = self.event_id(message)

    body = ERROR_NOT_AN_EVENT

    if event:
      today = datetime.date.today()
      day, month, year = int(day), int(month), int(year)

      if day in range(1, 32) and month in range(1, 13):
        # TODO: Date validation according to month and day.

        if year >= today.year and month >= today.month and day >= today.day:
          date_string = "%s-%02d-%02d" % (year, day, month)
          self.events[event_id]['date'] = date_string
          self.commit_events()
          body = MSG_DATE_SET % (month, day, year)
        else:
          body = ERROR_DATE_NOT_VALID % (month, day, year)
      else:
        body = ERROR_DATE_NOT_VALID % (month, day, year)

    return body

  def cmd_rsvp_set_time(self, message, hours='00', minutes='00'):
    event = self.get_this_event(message)
    event_id = self.event_id(message)

    if event:
      """
      Make sure the hours are in their valid range
      """
      hours, minutes = int(hours), int(minutes)

      if hours in range(0, 24) and minutes in range(0, 60):
        """
        We'll store the time as the number of seconds since 00:00
        """
        self.events[event_id]['time'] = '%02d:%02d' % (hours, minutes)
        self.commit_events()
        body = MSG_TIME_SET % (hours, minutes)
      else:
        body = ERROR_TIME_NOT_VALID % (hours, minutes)

    else:
      body = ERROR_NOT_AN_EVENT

    return body

  def cmd_rsvp_summary(self, message):
    event = self.get_this_event(message)
    event_id = self.event_id(message)

    if event:
      summary_table = '**%s**' % (event['name'])
      summary_table += '\t|\t\n:---:|:---:\n**What**|%s\n**When**|%s @ %s\n**Where**|%s\n'
      summary_table = summary_table % ('TODO', event['date'], event['time'] or '(All day)', 'TODO')


      confirmation_table = 'YES ({}) |NO ({}) \n:---:|:---:\n'
      confirmation_table = confirmation_table.format(len(event['yes']), len(event['no']))

      row_list = map(None, event['yes'], event['no'])

      for row in row_list:
        confirmation_table += '{}|{}\n'.format(
          '' if row[0] is None else row[0],
          '' if row[1] is None else row[1]
        )
      else:
        confirmation_table += '\t|\t'

      body = summary_table + '\n\n' + confirmation_table
    else:
      body = ERROR_NOT_AN_EVENT

    return body

  def cmd_rsvp_confirm(self, message, decision):
    # The event must exist.
    event = self.get_this_event(message)
    event_id = self.event_id(message)

    other_decision = 'no' if decision == 'yes' else 'yes'

    body = None

    if event:
      # Get the sender's name
      sender_name = message['sender_full_name']

      # Is he already in the list of attendees?
      if sender_name not in event[decision]:
        self.events[event_id][decision].append(sender_name)
        body = u'@**{}** is {} attending!'.format(sender_name, '' if decision == 'yes' else '**not**')

      # We need to remove him from the other decision's list, if he's there.
      if sender_name in event[other_decision]:
        self.events[event_id][other_decision].remove(sender_name)

      self.commit_events()
    else:
      body = ERROR_NOT_AN_EVENT

    return body

  def cmd_rsvp_init(self, message):

    subject = message['subject']
    body = 'This thread is now an RSVPBot event! Type `rsvp help` for more options.'
    event = self.get_this_event(message)

    if event:
      # Event already exists, error message, we can't initialize twice.
      body = ERROR_ALREADY_AN_EVENT
    else:
      # Update the dictionary with the new event and commit.
      self.events.update(
        {
          self.event_id(message): {
            'name': subject,
            'description': '',
            'creator': message['sender_id'],
            'yes': [],
            'no': [],
            'time': None,
            'date': '%s' % datetime.date.today(),
          }
        }
      )
      self.commit_events()

    return body

  def cmd_rsvp_help(self, message):
    body = """**Command**|**Description**\n--- | ---\n**`rsvp yes`**|Marks **you** as attending this event.\n**`rsvp no`**|Marks you as **not** attending this event.\n`rsvp init`|Initializes a thread as an RSVPBot event. Must be used before any other command.\n`rsvp help`|Shows this handy table.|\n`rsvp set time HH:mm`|Sets the time for this event (24-hour format) (optional)|\n`rsvp set date mm/dd/yyyy`|Sets the date for this event (optional)|\n`rsvp set description DESCRIPTION`|Sets this event's description to DESCRIPTION (optional)\n`rsvp set place PLACE_NAME`|Sets the place for this event to PLACE_NAME (optional)\n`rsvp cancel`|Cancels this event (can only be called by the caller of `rsvp init`)\n`rsvp summary`|Displays a summary of this event, including the description, and list of attendees.\n\nIf the event has a date and time, RSVPBot will automatically remind everyone who RSVP'd yes 10 minutes before the event gets started."""
    return body


  def cmd_rsvp_cancel(self, message):

    event = self.get_this_event(message)
    event_id = self.event_id(message)

    if not event:
      # The event does not exist. We cannot cancel it!
      body = ERROR_NOT_AN_EVENT
    else:

      # Check if the issuer of this command is the event's original creator.
      # Only he can delete the event.

      creator = event['creator']

      if creator == message['sender_id']:
        body = "The event has been canceled!"
        self.events.pop(event_id)
        self.commit_events()
      else:
        body = ERROR_NOT_AUTHORIZED_TO_DELETE
      # TODO: Notify everyone.

    return body


  def normalize_whitespace(self, content):
    # Strips trailing and leading whitespace, and normalizes contiguous 
    # Whitespace with a single space.
    content = content.strip()
    content = re.sub(r'\s+', ' ', content)
    return content