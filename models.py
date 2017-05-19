import secrets
from os import environ

import dateutil.parser
import pytz
import sqlalchemy

from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, validates
from sqlalchemy.inspection import inspect

import zulip_util
import rc
import strings

engine = create_engine(environ['DATABASE_URL'], echo=True)
Base = declarative_base()

session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    recurse_id = Column(Integer, unique=True)
    _created_at = Column("created_at", TIMESTAMP(timezone=True))
    created_by = Column(String)
    url = Column(String)
    timezone = Column(String)
    _start_time = Column("start_time", TIMESTAMP(timezone=True))
    _end_time = Column("end_time", TIMESTAMP(timezone=True))
    title = Column(String)
    stream = Column(String)
    subject = Column(String)

    @validates('stream', 'subject')
    def validate_stream_and_subject(self, key, field):
        if key is 'subject':
            only_one_set = self.stream and not field or field and not self.stream
            if only_one_set:
                raise ValueError("must set both stream and subject, or neither")

        return field

    @property
    def created_at(self):
        return self._created_at.astimezone(pytz.utc)

    @created_at.setter
    def created_at(self, value):
        self._created_at = value

    @property
    def start_time(self):
        return self._start_time.astimezone(pytz.timezone(self.timezone))

    @start_time.setter
    def start_time(self, value):
        self._start_time = value

    @property
    def end_time(self):
        return self._end_time.astimezone(pytz.timezone(self.timezone))

    @end_time.setter
    def end_time(self, value):
        self._end_time = value

    def update(self, **updates):
        assign_attributes(self, updates)
        Session.add(self)
        Session.commit()

    def refresh_from_api(self, include_participants=False):
        data = rc.get_event(self.recurse_id, include_participants=include_participants)
        event_data = event_dict(data)
        self.update(**event_data)
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

@sqlalchemy.event.listens_for(Event, 'before_insert')
def ensure_one_event_per_thread(mapper, conn, event):
    if event.already_initialized():
        thread_already_taken = Session.query(Event).filter(Event.stream == event.stream).filter(Event.subject == event.subject).count() > 0

        if thread_already_taken:
            zulip_util.send_message({
                "type": "stream",
                "display_recipient": event.stream,
                "subject": event.subject,
                "body": strings.ERROR_THREAD_FROM_RC_ALREADY_AN_EVENT.format(title=event.title, url=event.url)
            })
            rc.update_event(event.recurse_id, {
                'stream': None,
                'subject': None
            })
            raise ValueError('cannot add event to a thread already tracking another event')

@sqlalchemy.event.listens_for(Event, 'after_insert')
def announce_on_zulip(mapper, conn, event):
    if event.already_initialized():
        zulip_util.send_message({
            "type": "stream",
            "display_recipient": event.stream,
            "subject": event.subject,
            "body": strings.MSG_INIT_SUCCESSFUL.format(event.title, event.url)
        })
    else:
        zulip_util.announce_event(event)

@sqlalchemy.event.listens_for(Event, 'after_update')
def post_changes_to_zulip(mapper, conn, event):
    messages = []

    if event.already_initialized():
        changes = get_changes(event)

        if 'title' in changes:
            messages.append("The title has changed: " + event.title)

        if '_start_time' in changes or '_end_time' in changes:
            messages.append("The time has changed: " + event.timestamp())

    if messages:
        zulip_util.send_message({
            "type": "stream",
            "display_recipient": event.stream,
            "subject": event.subject,
            "body": "**This event has changed!**\n" + "\n".join(messages)
        })

@sqlalchemy.event.listens_for(Event, 'after_update')
def notify_rc_of_thread_changes(mapper, conn, event):
    if event.already_initialized():
        changes = get_changes(event)

        if 'stream' in changes or 'subject' in changes:
            rc.update_event(event.recurse_id, {
                'stream': event.stream,
                'subject': event.subject
            })

def assign_attributes(model, attributes):
    for k, v in attributes.items():
        setattr(model, k, v)
    return model

def event_dict(e):
    return {
        "recurse_id": e['id'],
        "created_at": parse_time(e, 'created_at', utc=True),
        "timezone": e['timezone'],
        "start_time": parse_time(e, 'start_time'),
        "end_time": parse_time(e, 'end_time'),
        "created_by": e['created_by']['name'],
        "url": e['url'],
        "title": e['title'],
        "stream": e['stream'],
        "subject": e['subject']
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

