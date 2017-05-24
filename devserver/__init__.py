from flask import Flask, render_template, url_for
import pytz
import datetime
import time
import dateutil.parser
import re
import random

app = Flask(__name__)

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
    parts = re.split(r',\s+', s)

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

def make_event(title, created_at, start_time, end_time, created_by, participant_count):
    to_participate = random.sample(users, participant_count)

    participants = [
        make_participant(user=user,
                         participant_number=i + 1,
                         created_at=created_at + datetime.timedelta(minutes=i*30))
        for i, user in enumerate(to_participate)
    ]

    id = random.randint(1, 100_000)

    return {
        "id": random.randint(1, 100_000),
        "title": title,
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


api_data = [
    make_event(
        "test event 1",
        created_at=time_from_english('1 day, 2 hours ago'),
        start_time=time_from_english('1 day, 1 hour ago'),
        end_time=time_from_english('1 day ago'),
        created_by=random.choice(users),
        participant_count=2
    ),
    make_event(
        "test event 2",
        created_at=time_from_english('3 days ago'),
        start_time=time_from_english('1 day from now'),
        end_time=time_from_english('1 day, 1 hour from now'),
        created_by=random.choice(users),
        participant_count=1
    ),
    make_event(
        "test event 3",
        created_at=time_from_english('30 minutes ago'),
        start_time=time_from_english('3 hours from now'),
        end_time=time_from_english('3 hours, 30 minutes from now'),
        created_by=random.choice(users),
        participant_count=3
    ),
]

@app.template_filter('dtformat')
def dtformat(value, format='%-m-%d-%Y at %H:%M'):
    return dateutil.parser.parse(value).strftime(format)

@app.route('/')
def hello():
    return render_template('index.html', title="Index", events=api_data)

@app.route('/reset', methods=['POST'])
def reset():
    return "Reset not implemented"

@app.route('/create', methods=['POST'])
def create():
    return "Create not implemented"



@app.route('/api/v1/events')
def events():
    pass

@app.route('/api/v1/events/<int:id>')
def event(id):
    pass

@app.route('/api/v1/events/<int:id>/join', methods=['POST'])
def join(id):
    pass

@app.route('/api/v1/events/<int:id>/leave', methods=['POST'])
def leave(id):
    pass

if __name__ == "__main__":
    app.run()
