from datetime import datetime, timedelta
import traceback
import time

import pytz

import rc
import models
from models import db, Event, make_event, parse_time

def utcnow():
    return datetime.utcnow().replace(tzinfo=pytz.utc)

def event_in(events, e):
    for event in events:
        if event.recurse_id == e['id']:
            return True
    return False

def event_not_in(events, e):
    return not event_in(events, e)

def remove_known_events(events):
    if not events:
        return []

    ids = [e['id'] for e in events]
    known_events = Event.query.filter(Event.recurse_id.in_(ids)).all()

    return [e for e in events if event_not_in(known_events, e)]

def fetch_new_events():
    oldest_event = Event.query.order_by(Event.created_at.desc()).first()

    if oldest_event is not None:
        created_at = oldest_event.created_at
    else:
        created_at = utcnow() - timedelta(days=60)

    now = utcnow()
    future_events = [e for e in rc.get_events(created_at_or_after=created_at) if parse_time(e, 'start_time') > now]

    return remove_known_events(future_events)

def fetch_and_insert_new_events():
    events = fetch_new_events()
    if events:
        records = [make_event(e) for e in events]
        db.session.add_all(records)
        db.session.commit()

def update_tracked_events():
    tracked = Event.query.filter(Event.stream != None).filter(Event.subject != None).filter(Event.start_time >= utcnow()).all()
    ids = [event.recurse_id for event in tracked]
    by_id = {event.recurse_id: event for event in tracked}

    if ids:
        for api_data in rc.get_events(ids=ids):
            event = by_id[api_data['id']]
            models.assign_attributes(event, models.event_dict(api_data))
            db.session.add(event)

        db.session.commit()

def run_poller():
    while True:
        try:
            fetch_and_insert_new_events()
            update_tracked_events()
        except BaseException:
            print(traceback.format_exc())

        time.sleep(15)
