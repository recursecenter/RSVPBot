import secrets
from os import environ

import dateutil.parser
import pytz
import sqlalchemy
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

import zulip_util
import rc

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

# TODO thread safety, we're using db & db.session on both threads
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recurse_id = db.Column(db.Integer, unique=True)
    created_at = db.Column(db.TIMESTAMP(timezone=True))
    created_by = db.Column(db.String)
    url = db.Column(db.String)
    start_time = db.Column(db.TIMESTAMP(timezone=True))
    end_time = db.Column(db.TIMESTAMP(timezone=True))
    title = db.Column(db.String)
    stream = db.Column(db.String)
    subject = db.Column(db.String)

    def update(self, **updates):
        assign_attributes(self, updates)
        db.session.add(self)
        db.session.commit()

    def refresh_from_api(self):
        c = rc.Client()
        self.update(**event_dict(c.get_event(self.recurse_id)))

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
    # TODO: session is probably not threadsafe
    db.session.add(event)
    db.session.commit()
    return event

def parse_time(event, attr, utc=False):
    if utc:
        tz = pytz.utc
    else:
        tz = pytz.timezone(event['timezone'])
    return dateutil.parser.parse(event[attr]).astimezone(tz)
