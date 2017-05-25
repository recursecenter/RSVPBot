# Do this early in case anything depends on .env
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from collections import Counter
from datetime import date, timedelta
import dateutil.parser
import os
import sys
from contextlib import contextmanager
import subprocess
import time
import random

import unittest
from unittest.mock import patch

from tap import TAPTestRunner

import requests

import config
import rc
import rsvp
import rsvp_commands
import strings
import models
from models import Event, Session, make_event

models.engine.echo = False

class RSVPTest(unittest.TestCase):
    def setUp(self):
        super().setUp()

        requests.post('http://localhost:{}/reset'.format(devserver_port))

        p1 = patch('zulip_util.announce_event')
        p2 = patch('zulip_util.send_message')
        self.addCleanup(p1.stop)
        self.addCleanup(p2.stop)
        p1.start()
        p2.start()

        self.rsvp = rsvp.RSVP('rsvp')

        test_events = rc.get_events(
            created_at_or_after=dateutil.parser.parse("2017-05-19T20:24:50.309192Z")
        )

        self.test_data1 = test_events[0]
        self.test_data2 = test_events[1]

        self.event, self.event2 = [make_event(self.test_data1), make_event(self.test_data2)]
        self._events = [self.event, self.event2]
        Session.add_all(self._events)
        Session.commit()

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
            sender_id=808, # Zach's Zulip id on recurse.zulipchat.com
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
        output = self.issue_command('rsvp init {}'.format(self.test_data2['id']))
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
            self.assertIn("RSVPBot doesn't support", output[0]['body'], "Incorrect message for command: " + command)

class RSVPMoveTest(RSVPTest):
    other_thread = {
        'display_recipient': 'other-stream',
        'subject': 'Other-Subject'
    }

    def test_move_event(self):
        stream = self.other_thread['display_recipient']
        subject = self.other_thread['subject']

        output = self.issue_command('rsvp move http://testhost/#narrow/stream/%s/subject/%s' % (stream, subject))

        self.assertEqual(self.event.stream, stream)
        self.assertEqual(self.event.subject, subject)
        self.assertEqual(2, len(output))

        self.assertIn("This event has been moved to **[#%s > %s]" % (stream, subject), output[0]['body'])
        self.assertIn("#narrow/stream/%s/subject/%s" % (stream, subject), output[0]['body'])
        self.assertIn("test-stream", output[0]['display_recipient'])
        self.assertIn("Testing", output[0]['subject'])

        self.assertIn("This thread is now an RSVPBot event", output[1]['body'])
        self.assertIn(stream, output[1]['display_recipient'])
        self.assertIn(subject, output[1]['subject'])

    def test_move_to_already_existing_event(self):
        stream = self.other_thread['display_recipient']
        subject = self.other_thread['subject']

        self.issue_command('rsvp init {}'.format(self.test_data2['id']), **self.other_thread)
        output = self.issue_command('rsvp move http://testhost/#narrow/stream/test-stream/subject/Testing', **self.other_thread)

        self.assertEqual(1, len(output))
        self.assertEqual(stream, self.event2.stream)
        self.assertEqual(subject, self.event2.subject)
        self.assertIn("Oops! #test-stream > Testing is already an RSVPBot event!", output[0]['body'])
        self.assertIn(stream, output[0]['display_recipient'])
        self.assertIn(subject, output[0]['subject'])

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
        self.assertIn(self.test_data1['location']['name'], body)
        self.assertIn(self.test_data1['description'], body)
        self.assertIn('Test User', body)

@unittest.skip
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


@contextmanager
def devserver(port):
    os.environ['PORT'] = str(port)
    config.rc_root = 'http://localhost:{}'.format(port)
    config.rc_api_root = config.rc_root + '/api/v1'

    proc = subprocess.Popen(['python', 'devserver/__init__.py'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # wait for the dev server to come up
    time.sleep(1)

    try:
        yield
    finally:
        proc.kill()
        proc.wait()

devserver_port = None

if __name__ == '__main__':
    devserver_port = random.randint(10000, 50000)

    with devserver(devserver_port):
        if os.getenv('HEROKU_CI', None):
            tests_dir = os.path.dirname(os.path.abspath(__file__))
            loader = unittest.TestLoader()
            tests = loader.discover(tests_dir)
            runner = TAPTestRunner()
            runner.set_stream(True)
            runner.set_outdir(False)

            result = runner.run(tests)
            if result.wasSuccessful():
                sys.exit(0)
            else:
                sys.exit(1)

        else:
            unittest.main()
