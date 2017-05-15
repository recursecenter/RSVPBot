import rc
import time
import dateutil.parser
import pytz

from server import db, Event
from datetime import datetime, timedelta


def parse_time(event, attr, utc=False):
    if utc:
        tz = pytz.utc
    else:
        tz = pytz.timezone(event['timezone'])
    return dateutil.parser.parse(event[attr]).astimezone(tz)

def utcnow():
    return datetime.utcnow().astimezone(pytz.utc)

def event_in(events, e):
    for event in events:
        if event.recurse_id == e['id']:
            return True
    return False

def event_not_in(events, e):
    return not event_in(events, e)

def fetch_new_events(client):
    oldest_event = Event.query.order_by(Event.created_at.desc()).first()

    if oldest_event is not None:
        created_at = oldest_event.created_at
    else:
        created_at = utcnow() - timedelta(days=60)

    now = utcnow()
    events = [e for e in client.get_events(created_at) if parse_time(e, 'start_time') > now]

    ids = [e['id'] for e in events]

    if ids:
        known_events = Event.query.filter(Event.recurse_id.in_(ids)).all()
    else:
        known_events = []

    return [e for e in events if event_not_in(known_events, e)]

def make_event(e):
    return Event(
        recurse_id=e['id'],
        created_at=parse_time(e, 'created_at', utc=True)
    )

def fetch_and_insert_new_events(client):
    events = fetch_new_events(client)
    if events:
        records = [make_event(e) for e in events]
        db.session.add_all(records)
        db.session.commit()

def update_tracked_events(client):
    # 2. update existing events
    # get all IDs we're tracking
    # fetch those events from RC API
    # update them in DB
    pass

def run_poller():
    client = rc.Client()

    while True:
        fetch_and_insert_new_events(client)
        update_tracked_events(client)
        time.sleep(15)
