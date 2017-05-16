from __future__ import with_statement
import re
import json

import rsvp_commands
from strings import ERROR_INVALID_COMMAND


class RSVP(object):

  def __init__(self, key_word, filename='events.json'):
    """
    When created, this instance will try to open self.filename. It will always
    keep a copy in memory of the whole events dictionary and commit it when necessary.
    """
    self.key_word = key_word
    self.filename = filename
    self.command_list = (
      rsvp_commands.RSVPInitCommand(key_word),
      rsvp_commands.RSVPHelpCommand(key_word),
      rsvp_commands.RSVPMoveCommand(key_word),
      rsvp_commands.RSVPSummaryCommand(key_word),
      rsvp_commands.RSVPPingCommand(key_word),
      rsvp_commands.RSVPCreditsCommand(key_word),

      # Command supported on recurse.com
      rsvp_commands.RSVPCancelCommand(key_word),
      rsvp_commands.RSVPSetLimitCommand(key_word),
      rsvp_commands.RSVPSetDateCommand(key_word),
      rsvp_commands.RSVPSetTimeCommand(key_word),
      rsvp_commands.RSVPSetTimeAllDayCommand(key_word),
      rsvp_commands.RSVPSetDurationCommand(key_word),
      rsvp_commands.RSVPSetLocationCommand(key_word),
      rsvp_commands.RSVPSetPlaceCommand(key_word),
      rsvp_commands.RSVPSetDescriptionCommand(key_word),

      # Command no longer supported anywhere
      rsvp_commands.RSVPCreateCalendarEventCommand(key_word),

      # This needs to be at last for fuzzy yes|no checking
      rsvp_commands.RSVPConfirmCommand(key_word)
    )

    try:
      with open(self.filename, "r") as f:
        try:
          self.events = json.load(f)
        except ValueError:
          self.events = {}
    except IOError:
      self.events = {}

  def commit_events(self):
    """Write the whole events dictionary to the filename file."""
    with open(self.filename, 'w+') as f:
      json.dump(self.events, f)

  def __exit__(self, type, value, traceback):
    """Before the program terminates, commit events."""
    self.commit_events()

  def process_message(self, message):
    """Processes the received message and returns a new message, to send back to the user."""

    # adding handling of mulitples, dammit.
    replies = self.route(message)
    messages = []

    for reply in replies:
      # only reply via PM to incoming PMs
      if message['type'] == 'private':
        reply.type = 'private'

      if not reply.to:
        # this uses invisible side effects and I don't care for it.
        messages.append(self.create_message_from_message(message, reply.body))
      else:
        # this is sending to a stream other than the one the incoming message
        messages.append(self.format_message(reply))

    return messages

  def route(self, message):
    """Split multiple line message and collate the responses."""
    content = message['content']
    responses = []
    lines = normalize_whitespace(content)
    for line in lines:
      responses.extend(self.route_internal(message, line))
    return responses

  def route_internal(self, message, content):
    """Route message to matching command.

    To be a valid rsvp command, the string must start with the string rsvp.
    To ensure that we can match things exactly, we must remove the extra whitespace.
    We then pattern-match it with every known command pattern.
    If there's absolutely no match, we return None, which, for the purposes of this program,
    means no reply.
    """
    regex = r'^{}'.format(self.key_word)

    if re.match(regex, content, flags=re.I):
      for command in self.command_list:
        matches = command.match(content)
        if matches:
          kwargs = {
            'sender_email': message['sender_email'],
            'sender_full_name': message['sender_full_name'],
            'sender_id': message['sender_id'],
            'stream': message['display_recipient'],
            'subject': message['subject'],
          }

          if matches.groupdict():
            kwargs.update(matches.groupdict())

          response = command.execute(self.events, **kwargs)

          # Allow for a single events object but multiple messaages to send
          self.events = response.events
          self.commit_events()

          # if it has multiple messages to send, then return that instead of
          # the pair
          return response.messages

      return [rsvp_commands.RSVPMessage('private', ERROR_INVALID_COMMAND % (content), message['sender_email'])]
    return [rsvp_commands.RSVPMessage('private', None)]


  def create_message_from_message(self, message, body):
    """Convenience method for creating a zulip response message from a
    given zulip input message.
    """
    if body:
      return {
        'subject': message['subject'],
        'display_recipient': message['display_recipient'],
        'sender_email': message['sender_email'],
        'type': message['type'],
        'body': body
      }


  def format_message(self, message):
    """Convenience method for creating a zulip response message from an RSVP message."""
    return {
      'subject': message.subject,
      'display_recipient': message.to,
      'type': message.type,
      'body': message.body
    }


def normalize_whitespace(content):
    """Strips trailing and leading whitespace from each line, and normalizes contiguous
    whitespace with a single space.
    """
    return [re.sub(r'\s+', ' ', line.strip()) for line in content.strip().split('\n')]
