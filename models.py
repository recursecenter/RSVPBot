import secrets
from os import environ

import dateutil.parser
import pytz
import sqlalchemy

from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.inspection import inspect

import zulip_util
import rc

engine = create_engine(environ['DATABASE_URL'], echo=True)
Base = declarative_base()

session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

class Event(Base):
    __tablename__ = 'event'

    id = Column(Integer, primary_key=True)
    recurse_id = Column(Integer, unique=True)
    created_at = Column(TIMESTAMP(timezone=True))
    created_by = Column(String)
    url = Column(String)
    start_time = Column(TIMESTAMP(timezone=True))
    end_time = Column(TIMESTAMP(timezone=True))
    title = Column(String)
    stream = Column(String)
    subject = Column(String)

    def update(self, **updates):
        assign_attributes(self, updates)
        Session.add(self)
        Session.commit()

    def refresh_from_api(self, include_participants=False):
        data = rc.get_event(self.recurse_id, include_participants=include_participants)
        self.update(**event_dict(data))
        return data

    def already_initialized(self):
        return bool(self.stream or self.subject)

    # 5–7pm EDT, Wednesday, May 17, 2017
    def timestamp(self):
        start = self.start_time.strftime("%-I:%M%p").lower()
        end = self.end_time.strftime("%-I:%M%p").lower()
        zone = self.start_time.tzinfo.tzname(self.start_time)
        date = self.start_time.strftime("%A, %b %-d, %Y")

        return "{}–{} {}, {}".format(start, end, zone, date)

    def zulip_link(self):
        # This format doesn't autolink yet. Should create an issue for it.
        # return "#**{} > {}**".format(self.stream, self.subject)

        url = zulip_util.stream_topic_to_narrow_url(self.stream, self.subject)
        return "**[#{} > {}]({})**".format(self.stream, self.subject, url)

@sqlalchemy.event.listens_for(Event, 'after_insert')
def announce_on_zulip(mapper, conn, event):
    zulip_util.announce_event(event)

@sqlalchemy.event.listens_for(Event, 'after_update')
def post_changes_to_zulip(mapper, conn, event):
    messages = []

    if event.already_initialized():
        changes = get_changes(event)

        if 'title' in changes:
            messages.append("The title has changed: " + event.title)

        if 'start_time' in changes or 'end_time' in changes:
            messages.append("The time has changed: " + event.timestamp())

    if messages:
        zulip_util.send_message({
            "type": "stream",
            "display_recipient": event.stream,
            "subject": event.subject,
            "body": "**This event has changed!**\n" + "\n".join(messages)
        })

def assign_attributes(model, attributes):
    for k, v in attributes.items():
        setattr(model, k, v)
    return model

def event_dict(e):
    return {
        "recurse_id": e['id'],
        "created_at": parse_time(e, 'created_at', utc=True),
        "start_time": parse_time(e, 'start_time'),
        "end_time": parse_time(e, 'end_time'),
        "created_by": e['created_by']['name'],
        "url": e['url'],
        "title": e['title']
    }

def make_event(e):
    return Event(**event_dict(e))

def insert_event(e):
    event = make_event(e)
    Session.add(event)
    Session.commit()
    return event

def parse_time(event, attr, utc=False):
    if utc:
        tz = pytz.utc
    else:
        tz = pytz.timezone(event['timezone'])
    return dateutil.parser.parse(event[attr]).astimezone(tz)

def get_changes(obj):
    state = inspect(obj)
    changes = {}

    for attr in state.attrs:
        history = state.get_history(attr.key, True)
        if history.has_changes():
            changes[attr.key] = history.added

    return changes

