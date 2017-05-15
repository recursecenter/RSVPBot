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

def run_poller():
    c = rc.Client()

    while True:
        # 1. fetch new events
        # get latest event created_at stamp
        # if there is none, let it be something a long, long time ago
        # use created_at to fetch events after it
        # filter events to those that haven't already started
        # add them to DB if they're not already there
        oldest_event = Event.query.order_by(Event.created_at.desc()).first()

        if oldest_event is not None:
            created_at = oldest_event.created_at
        else:
            created_at = utcnow() - timedelta(days=60)

        now = utcnow()
        _events = c.get_events(created_at)
        events = [e for e in _events if parse_time(e, 'start_time') > now]

        ids = [e['id'] for e in events]

        if ids:
            known_events = Event.query.filter(Event.recurse_id.in_(ids)).all()
        else:
            known_events = []

        events_to_add = [e for e in events if event_not_in(known_events, e)]

        db.session.add_all([
            Event(recurse_id=e['id'], created_at=parse_time(e, 'created_at', utc=True)) for e in events_to_add
        ])
        db.session.commit()

        # 2. update existing events
        # get all IDs we're tracking
        # fetch those events from RC API
        # update them in DB

        time.sleep(15)

