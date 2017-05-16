import sqlalchemy
import secrets

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from os import environ

import zulip_util

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

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

    # 5–7pm EDT, Wednesday, May 17, 2017
    def timestamp(self):
        start = self.start_time.strftime("%-I:%M%p").lower()
        end = self.end_time.strftime("%-I:%M%p").lower()
        zone = self.start_time.tzinfo.tzname(self.start_time)
        date = self.start_time.strftime("%A, %b %-d, %Y")

        return "{}–{} {}, {}".format(start, end, zone, date)

@sqlalchemy.event.listens_for(Event, 'after_insert')
def announce_on_zulip(mapper, conn, event):
    zulip_util.announce_event(event)
