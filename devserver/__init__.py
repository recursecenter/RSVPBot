import datetime
import time
import re
import random
import os
from copy import deepcopy
import json

from flask import Flask, render_template, url_for, request, redirect
from flask.json import jsonify
import pytz
import dateutil.parser

app = Flask(__name__)

def utcnow():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)

def ensure_plural(s):
    if s.endswith('s'):
        return s
    else:
        return s + 's'

# "3 days, 1 hour, 2 minutes ago" etc.
def time_from_english(s):
    if s == 'now':
        return utcnow()

    # "3 days, 1 hour, 2 minutes ago" => ["3 days", "1 hour", "2 minutes ago"]
    parts = re.split(r',\s*', s)

    # "2 minutes ago" => ["2", "minutes", "ago"]
    # "3 days from now" => ["3", days", "from now"]
    last_number, last_unit, direction = parts[-1].split(maxsplit=2)
    parts[-1] = "{} {}".format(last_number, last_unit)

    split_parts = [part.split() for part in parts]

    if direction == 'from now':
        multiplier = 1
    elif direction == 'ago':
        multiplier = -1
    else:
        raise RuntimeError("Unknown direction: {}".format(direction))

    delta_args = {ensure_plural(units): int(number) * multiplier for number, units in split_parts}

    return (utcnow() + datetime.timedelta(**delta_args))

def make_participant(user, participant_number, created_at):
    return {
        "id": random.randint(1, 100_000),
        "participant_number": participant_number,
        "created_at": created_at.isoformat(),
        "person": {
            **user,
        }
    }


next_event_id = 1

def make_event(created_at, start_time, end_time, created_by, participant_count):
    to_participate = random.sample(users, participant_count)

    participants = [
        make_participant(user=user,
                         participant_number=i + 1,
                         created_at=created_at + datetime.timedelta(minutes=i*30))
        for i, user in enumerate(to_participate)
    ]

    global next_event_id
    id = next_event_id
    next_event_id += 1

    return {
        "id": id,
        "title": "test event {}".format(id),
        "description": "Lorem ipsum dolor sit amet, consectetur adipisicing elit",
        "category": "programming_and_education",
        "rsvp_capacity": None,
        "allow_guests": False,
        "archived": False,
        "anonymize_participants": False,
        "participant_count": participant_count,
        "stream": None,
        "subject": None,
        "created_at": created_at.isoformat(),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "rsvp_deadline": None,
        "timezone": "America/New_York",
        "url": "https://www.recurse.com/calendar/{}".format(id),
        "created_by": {
            **created_by,
        },
        "location": {
            "id": 1,
            "name": "Recurse Center",
            "address": "455 Broadway, 2nd Floor",
            "city": "New York City, NY",
        },
        "participants": participants,
    }

users = [
    {
        "id": 1,
        "name": "Test User A",
        "first_name": "Test",
        "profile_path": "/directory/1-test-user-a",
        "image_path": "/assets/people/test_user_a_150.jpg",
        "zulip_id": 100,
    },
    {
        "id": 2,
        "name": "Test User B",
        "first_name": "Test",
        "profile_path": "/directory/2-test-user-b",
        "image_path": "/assets/people/test_user_b_150.jpg",
        "zulip_id": 101,
    },
    {
        "id": 3,
        "name": "Test User C",
        "first_name": "Test",
        "profile_path": "/directory/3-test-user-c",
        "image_path": "/assets/people/test_user_c_150.jpg",
        "zulip_id": 102,
    },
    {
        "id": 4,
        "name": "Test User D",
        "first_name": "Test",
        "profile_path": "/directory/4-test-user-d",
        "image_path": "/assets/people/test_user_d_150.jpg",
        "zulip_id": 103,
    },
]

original_api_data = [
    make_event(
        created_at=time_from_english('1 day, 2 hours ago'),
        start_time=time_from_english('1 day, 1 hour ago'),
        end_time=time_from_english('1 day ago'),
        created_by=random.choice(users),
        participant_count=2
    ),
    make_event(
        created_at=time_from_english('3 days ago'),
        start_time=time_from_english('3 hours from now'),
        end_time=time_from_english('3 hours, 30 minutes from now'),
        created_by=random.choice(users),
        participant_count=1
    ),
    make_event(
        created_at=time_from_english('30 minutes ago'),
        start_time=time_from_english('1 day from now'),
        end_time=time_from_english('1 day, 1 hour from now'),
        created_by=random.choice(users),
        participant_count=3
    ),
]

api_data = deepcopy(original_api_data)

@app.template_filter('dtformat')
def dtformat(value, format='%-m-%d-%Y at %H:%M'):
    return dateutil.parser.parse(value).strftime(format)


def sort_by_start_time(events):
    return sorted(events, key=lambda e: dateutil.parser.parse(e['start_time']))

@app.route('/')
def index():
    return render_template('index.html', title="Index", events=sort_by_start_time(api_data), flask_debug_mode=os.getenv('FLASK_DEBUG'))

@app.route('/reset', methods=['POST'])
def reset():
    global next_event_id, api_data
    next_event_id = 1
    api_data = deepcopy(original_api_data)

    return redirect(url_for('index'))

@app.route('/create', methods=['POST'])
def create():
    days = random.randint(1, 10)
    hours = random.randint(1, 10)

    start_time = time_from_english("{} days, {} hours from now".format(days, hours))
    end_time = start_time + datetime.timedelta(minutes=30)

    event = make_event(
        created_at=utcnow(),
        start_time=start_time,
        end_time=end_time,
        created_by=random.choice(users),
        participant_count=random.randint(0, len(users) - 1)
    )

    api_data.append(event)

    return redirect(url_for('index'))


# parses a date and sets tzinfo to UTC if it is not set.
# otherwise we'll fail later
def parse_date(s):
    date = dateutil.parser.parse(s)

    if not date.tzinfo:
        date = date.replace(tzinfo=pytz.utc)

    return date

def created_on_or_after(event, date):
    return dateutil.parser.parse(event['created_at']) >= date

def find_event(id):
    return next((e for e in api_data if e['id'] == id), None)

def filter_participants(event):
    include_participants = request.args.get('include_participants', '').lower()
    if include_participants == 'true':
        return event
    else:
        return {k: v for k, v in event.items() if k != 'participants'}

def render_event(event):
    return jsonify(filter_participants(event))

def render_events(events):
    return jsonify([filter_participants(event) for event in events])

@app.route('/api/v1/events')
def events():
    if 'created_at_or_after' in request.args:
        date = parse_date(request.args['created_at_or_after'])
        events = [event for event in api_data if created_on_or_after(event, date)]
        return render_events(sort_by_start_time(events))
    elif 'ids' in request.args:
        ids = json.loads(request.args['ids'])
        return render_events(e for e in map(find_event, ids) if e)
    else:
        return render_events([])

def not_found():
    response = jsonify({"message":"not_found"})
    response.status_code = 404
    return response

def user_not_specified():
    response = jsonify({"message": "user_not_specified"})
    response.status_code = 422
    return response

@app.route('/api/v1/events/<int:id>', methods=['GET'])
def event(id):
    event = find_event(id)
    if event == None:
        return not_found()

    return render_event(event)


def slice(dict, *keys):
    if dict == None:
        return {}

    return {k: v for k, v in dict.items() if k in keys}

update_attributes = ['stream', 'subject']

@app.route('/api/v1/events/<int:id>', methods=['PATCH'])
def update_event(id):
    event = find_event(id)
    if event == None:
        return not_found()

    j = request.get_json()

    if not j or 'event' not in j:
       return render_event(event)

    updates = slice(j['event'], *update_attributes)

    for k, v in updates.items():
        event[k] = v

    return render_event(event)

# If user_param and user_param_value are set correctly
# find_user will always return a user, regardless of
# what zulip_id is submitted.
def find_user(user_param, user_param_value):
    if user_param != 'zulip_id' or user_param_value == None:
        return None

    try:
        zulip_id = int(user_param_value)
    except ValueError:
        return None

    return users[zulip_id % len(users)]

def find_participant(user, event):
    for participant in event['participants']:
        if participant['person'] == user:
            return participant

    return None

def leave_event(user, event):
    participant = find_participant(user, event)

    if participant:
        event['participants'] = [p for p in event['participants'] if p != participant]

def join_event(user, event):
    participant = find_participant(user, event)

    if not participant:
        next_participant_number = len(event['participants']) + 1
        participant = make_participant(user=user,
                                       participant_number=next_participant_number,
                                       created_at=utcnow())
        event['participants'].append(participant)

@app.route('/api/v1/events/<int:id>/join', methods=['POST'])
def join(id):
    event = find_event(id)
    if event == None:
        return not_found()

    user = find_user(request.args.get('user_param'), request.args.get('user_param_value'))
    if user == None:
        return user_not_specified()

    join_event(user, event)

    return jsonify({
        'joined': True,
        'rsvps_disabled': False,
        'event_archived': False,
        'over_capacity': False,
        'past_deadline': False,
    })

@app.route('/api/v1/events/<int:id>/leave', methods=['POST'])
def leave(id):
    event = find_event(id)
    if event == None:
        return not_found()

    user = find_user(request.args.get('user_param'), request.args.get('user_param_value'))
    if user == None:
        return user_not_specified()

    leave_event(user, event)

    return jsonify({})


if __name__ == "__main__":
    app.run(port=int(os.getenv('PORT', 5000)), threaded=True)
