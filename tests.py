from collections import Counter
from datetime import date, timedelta
import os

import unittest
from unittest.mock import patch

from tap import TAPTestRunner

import rsvp
import rsvp_commands
import strings
import models
from models import Event, Session, make_event

models.engine.echo = False

test_data_with_participants = {
    'id': 123456789,
    'title': 'VisiData workshop for users',
    'description': 'Learn how to use VisiData, a terminal-based tool for rapid exploration of tabular data.  Bring a data file and start browsing in seconds!',
    'category': 'programming_and_education',
    'rsvp_capacity': None,
    'allow_guests': False,
    'archived': False,
    'anonymize_participants': False,
    'participant_count': 3,
    'created_at': '2017-05-05T01:39:33-04:00',
    'start_time': '2017-05-24T15:00:00-04:00',
    'end_time': '2017-05-24T16:00:00-04:00',
    'rsvp_deadline': None,
    'timezone': 'America/New_York',
    'url': 'http://localhost:5000/calendar/123456789',
    'created_by': {
        'id': 2205,
        'name': 'Saul Pwanson',
        'first_name': 'Saul',
        'profile_path': '/directory/2205-saul-pwanson',
        'image_path': '/assets/people/saul_pwanson_150.jpg'
    },
    'location': {
        'id': 2,
        'name': 'Hopper - Recurse Center',
        'address': '455 Broadway, 2nd Floor',
        'city': 'New York City, NY'
    },
    'participants': [{
        'id': 594,
        'participant_number': 1,
        'created_at_utc': 1493962773,
        'person': {
            'id': 2205,
            'name': 'Saul Pwanson',
            'zulip_id': 100791,
            'profile_path': '/directory/2205-saul-pwanson',
            'image_path': '/assets/people/saul_pwanson_50.jpg'
        }
    },{
        'id': 1222,
        'participant_number': 2,
        'created_at_utc': 1494380829,
        'person': {
            'id': 34,
            'name': 'Nick Bergson-Shilcock',
            'zulip_id': 811,
            'profile_path': '/directory/34-nick-bergson-shilcock',
            'image_path': '/assets/people/nick_bergson-shilcock_50.jpg'
        }
    },{
        'id': 1315,
        'participant_number': 3,
        'created_at_utc': 1494974491,
        'person': {
            'id': 36,
            'name': 'David Albert',
            'zulip_id': 599,
            'profile_path': '/directory/36-david-albert',
            'image_path': '/assets/people/david_albert_50.jpg'
        }
    }]
}
test_data_with_participants_2 = {
    **test_data_with_participants,
    'id': 987654321,
    'url': 'http://localhost:5000/calendar/987654321'
}

test_data = {k: v for k, v in test_data_with_participants.items() if k != 'participants'}
test_data_2 = {k: v for k, v in test_data_with_participants_2.items() if k != 'participants'}

api_data = {
    test_data['id']: {
        True: test_data_with_participants,
        False: test_data
    },
    test_data_2['id']: {
        True: test_data_with_participants_2,
        False: test_data_2
    }
}

class MockClient():
    def get_event(self, id, include_participants=False):
        data = api_data.get(id)

        if data:
            return data[include_participants]
        else:
            return None

    def get_events(self, created_at_or_after=None, ids=None):
        raise NotImplementedError("get_events hasn't been mocked yet")

    def join(self, event_id, zulip_id):
        if event_id != test_data['id']:
            raise RuntimeError('unknown event_id for join')

        return {
            'joined': True,
            'rsvps_disabled': False,
            'event_archived': False,
            'over_capacity': False,
            'past_deadline': False
        }

    def leave(self, event_id, zulip_id):
        return {}

class RSVPTest(unittest.TestCase):
    def insert_event(self, data):
        event = make_event(data)
        Session.add(event)
        Session.commit()
        self._events.append(event)
        return event

    def setUp(self):
        p1 = patch('rc.Client', MockClient)
        p2 = patch('zulip_util.announce_event')
        self.addCleanup(p1.stop)
        self.addCleanup(p2.stop)
        p1.start()
        p2.start()

        self._events = []
        self.rsvp = rsvp.RSVP('rsvp')
        self.event = self.insert_event(test_data)
        self.issue_command('rsvp init {}'.format(self.event.url))


    def tearDown(self):
        for event in self._events:
            Session.delete(event)
        Session.commit()

    def create_input_message(
            self,
            content='',
            message_type='stream',
            display_recipient='test-stream',
            subject='Testing',
            sender_id=12345,
            sender_full_name='Tester',
            sender_email='test@example.com'):

        return {
            'content': content,
            'subject': subject,
            'display_recipient': display_recipient,
            'sender_id': sender_id,
            'sender_full_name': sender_full_name,
            'sender_email': sender_email,
            'type': message_type,
        }

    def issue_command(self, command, **kwargs):
        message = self.create_input_message(content=command, **kwargs)
        return self.rsvp.process_message(message)

class RSVPInitTest(RSVPTest):
    def test_event_init(self):
        self.assertEqual('test-stream', self.event.stream)
        self.assertEqual('Testing', self.event.subject)

    def test_cannot_double_init(self):
        output = self.issue_command('rsvp init {}'.format(test_data['id']))
        self.assertIn('is already an RSVPBot event', output[0]['body'])

class RSVPFunctionalityMovedTest(RSVPTest):
    def test_functionality_moved(self):
        commands = [
            'set limit 5',
            'set date foo',
            'set time 10:00',
            'set duration foo'
            'set location foo',
            'set place foo',
            'set description foo'
            'cancel',
        ]
        for command in commands:
            output = self.issue_command('rsvp ' + command)
            self.assertIn("RSVPBot doesn't support", output[0]['body'])

class RSVPMoveTest(RSVPTest):
    def test_move_event(self):
        output = self.issue_command('rsvp move http://testhost/#narrow/stream/test-move/subject/MovedTo')

        self.assertEqual(self.event.stream, 'test-move')
        self.assertEqual(self.event.subject, 'MovedTo')
        self.assertEqual(2, len(output))

        self.assertIn("This event has been moved to **[#test-move > MovedTo]", output[0]['body'])
        self.assertIn("#narrow/stream/test-move/subject/MovedTo", output[0]['body'])
        self.assertIn("test-stream", output[0]['display_recipient'])
        self.assertIn("Testing", output[0]['subject'])

        self.assertIn("This thread is now an RSVPBot event", output[1]['body'])
        self.assertIn("test-move", output[1]['display_recipient'])
        self.assertIn("MovedTo", output[1]['subject'])

    def test_move_to_already_existing_event(self):
        event2 = self.insert_event(test_data_2)
        other_thread = {
            'display_recipient': 'other-stream',
            'subject': 'Other Subject'
        }

        self.issue_command('rsvp init {}'.format(test_data_2['id']), **other_thread)
        output = self.issue_command('rsvp move http://testhost/#narrow/stream/test-stream/subject/Testing', **other_thread)

        self.assertEqual(1, len(output))
        self.assertEqual('other-stream', event2.stream)
        self.assertEqual('Other Subject', event2.subject)
        self.assertIn("Oops! #test-stream > Testing is already an RSVPBot event!", output[0]['body'])
        self.assertIn("other-stream", output[0]['display_recipient'])
        self.assertIn("Other Subject", output[0]['subject'])

class RSVPDecisionTest(RSVPTest):
    def test_generate_response_yes(self):
        command = rsvp_commands.RSVPConfirmCommand(prefix='rsvp')
        response = command.generate_response('yes', self.event)
        self.assertIn("**You** are attending", response)

    def test_generate_response_no(self):
        command = rsvp_commands.RSVPConfirmCommand(prefix='rsvp')
        response = command.generate_response('no', self.event)
        self.assertIn("You are **not** attending", response)

    def test_generate_funky_response_yes(self):
        command = rsvp_commands.RSVPConfirmCommand(prefix='rsvp')
        normal_response = command.generate_response('yes', self.event)
        possible_expected_responses = [prefix + normal_response for prefix in command.funky_yes_prefixes]
        response = command.generate_response('yes', self.event, funkify=True)
        self.assertIn(response, possible_expected_responses)

    def test_generate_funky_response_no(self):
        command = rsvp_commands.RSVPConfirmCommand(prefix='rsvp')
        normal_response = command.generate_response('no', self.event)
        possible_expected_responses = [normal_response + postfix for postfix in command.funky_no_postfixes]
        response = command.generate_response('no', self.event, funkify=True)
        self.assertIn(response, possible_expected_responses)

    def test_rsvp_yes(self):
        output = self.issue_command('rsvp yes')
        self.assertIn("**You** are attending", output[0]['body'])

    def test_rsvp_maybe(self):
        output = self.issue_command('rsvp maybe')
        self.assertEqual(strings.ERROR_RSVP_MAYBE_NOT_SUPPORTED, output[0]['body'])

    def test_rsvp_no(self):
        output = self.issue_command('rsvp no')
        self.assertIn('You are **not** attending', output[0]['body'])

    def general_yes(self, msg):
        output = self.issue_command(msg)
        self.assertIn('are attending', output[0]['body'])

    def general_no(self, msg):
        output = self.issue_command(msg)
        self.assertIn('are **not** attending', output[0]['body'])

    def test_rsvp_hell_yes(self):
        self.general_yes('rsvp hell yes')

    def test_rsvp_hell_yes_with_no(self):
        self.general_yes('rsvp hell to the yes I have no plans!')

    def test_rsvp_yes_plz(self):
        self.general_yes('rsvp yes plz!')

    def test_rsvp_yes_with_nose_in_it(self):
        self.general_yes('rsvp yes, after my nose job')

    def test_rsvp_yes_no(self):
        self.general_yes('rsvp yes no')

    def test_rsvp_yessssssssssss(self):
        self.general_yes('rsvp yesssssssssss')

    def test_rsvp_yassssssssssss(self):
        self.general_yes('rsvp yasssssssssss')

    def test_rsvp_thumbsup(self):
        self.general_yes('rsvp :thumbsup:')

    def test_rsvp_thumbs_up(self):
        self.general_yes('rsvp :thumbs_up:')

    def test_rsvp_thumbsdown(self):
        self.general_no('rsvp :thumbsdown:')

    def test_rsvp_thumbs_down(self):
        self.general_no('rsvp :thumbs_down:')

    def test_rsvp_plus_one(self):
        self.general_yes('rsvp :+1:')

    def test_rsvp_minus_one(self):
        self.general_no('rsvp :-1:')

    def test_rsvp_y(self):
        self.general_yes('rsvp y')

    def test_rsvp_n(self):
        self.general_no('rsvp n')

    def test_rsvp_hell_no(self):
        self.general_no('rsvp hell no!')

    def test_rsvp_no_way(self):
        self.general_no('rsvp no, i\'m busy')

    def test_rsvp_nah(self):
        self.general_no("rsvp nah can't make it :(!")

    def test_rsvp_noooooo(self):
        self.general_no('rsvp nooooooooooooo!')

    def test_rsvp_no_yes(self):
        self.general_no('rsvp no, yes i was there yesterday.')

    def rsvp_word_contains_command(self, msg):
        output = self.issue_command(msg)
        self.assertIn('is not a valid RSVPBot command!', output[0]['body'])

    def test_rsvp_nose(self):
        self.rsvp_word_contains_command('rsvp nose jobs')

    def test_rsvp_yesterday(self):
        self.rsvp_word_contains_command('rsvp yesterday')

    def test_rsvp_eyes(self):
        self.rsvp_word_contains_command('rsvp eyes')

    def test_rsvp_no_eyes(self):
        self.general_no('rsvp no eyes')

    def test_rsvp_yes_exclamation_no_plans(self):
        self.general_yes('rsvp yes! i couldn\'t say no')

    def test_rsvp_NO(self):
        self.general_no('rsvp hell NO!')

    def test_RSVP_yes_way(self):
        self.general_yes('RSVP yes plz')

class RSVPSummaryTest(RSVPTest):
    @patch('zulip_util.get_names', return_value=['Test User'])
    def test_summary(self, mock_get_names):
        output = self.issue_command('rsvp summary')
        body = output[0]['body']

        self.assertIn(self.event.title, body)
        self.assertIn(self.event.timestamp(), body)
        self.assertIn(test_data['location']['name'], body)
        self.assertIn(test_data['description'], body)
        self.assertIn('Test User', body)

@patch('zulip_util.get_names', return_value=['A', 'B'])
class RSVPPingTest(RSVPTest):
    def test_ping(self, mock_get_names):
        body = self.issue_command('rsvp ping')[0]['body']

        self.assertIn('@**A**', body)
        self.assertIn('@**B**', body)

    def test_ping_message(self, mock_get_names):
        body = self.issue_command('rsvp ping message!!!')[0]['body']

        self.assertIn('@**A**', body)
        self.assertIn('message!!!', body)

    def test_rsvp_ping_with_yes(self, mock_get_names):
        body = self.issue_command('rsvp ping we\'re all going to the yes concert')[0]['body']

        self.assertIn('@**B**', body)
        self.assertIn("we're all going to the yes concert", body)


class RSVPHelpTest(RSVPTest):
    def test_rsvp_help_generates_markdown_table(self):
        output = self.issue_command('rsvp help')
        header = """
**Command**|**Description**
--- | ---
        """.strip()
        self.assertIn(header, output[0]['body'])

    def test_rsvp_help_contains_help_for_all_commands(self):
        # FIXME: currently enumerating commands manually, which is brittle.
        # Being able to get a list of all commands
        commands = (
            "yes",
            "no",
            "init",
            "help",
            "ping",
            "move",
            "summary",
            "credits"
        )
        output = self.issue_command('rsvp help')
        for command in commands:
            self.assertIn("`rsvp %s" % command, output[0]['body'])


class RSVPMessageTypesTest(RSVPTest):
    def test_rsvp_private_message(self):
        output = self.issue_command('rsvp yes', message_type='private')
        self.assertEqual('private', output[0]['type'])
        self.assertEqual('test@example.com', output[0]['display_recipient'])

    def test_rsvp_help_replies_privately(self):
        output = self.issue_command('rsvp help')
        self.assertEqual(output[0]['display_recipient'], 'test@example.com')
        self.assertEqual(output[0]['type'], 'private')


class RSVPMultipleCommandsTest(RSVPTest):
    def test_rsvp_multiple_commands(self):
        commands = """
rsvp yes
rsvp no
"""
        output = self.issue_command(commands)

        self.assertIn('**You** are attending', output[0]['body'])
        self.assertIn('You are **not** attending', output[1]['body'])

    def test_rsvp_multiple_commands_with_other_text(self):
        commands = """
rsvp yes
Looking forward to this!
rsvp no
"""

        output = self.issue_command(commands)

        self.assertIn('**You** are attending', output[0]['body'])
        self.assertEqual(None, output[1])
        self.assertIn('You are **not** attending', output[2]['body'])


if __name__ == '__main__':
    if os.getenv('HEROKU_CI', None):
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        loader = unittest.TestLoader()
        tests = loader.discover(tests_dir)
        runner = TAPTestRunner()
        runner.set_stream(True)
        runner.set_outdir(False)
        runner.run(tests)
    else:
        unittest.main()
