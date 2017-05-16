import sqlalchemy
import secrets

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from os import environ

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recurse_id = db.Column(db.Integer, unique=True)
    token = db.Column(db.String, unique=True)
    created_at = db.Column(db.TIMESTAMP(timezone=True))

    def to_dict(self):
      return {
        'recurse_id': self.recurse_id,
        'token': self.token
      }

@sqlalchemy.event.listens_for(Event, 'before_insert')
def set_token(mapper, conn, event):
    while True:
        token = secrets.token_hex(16)
        if Event.query.filter(Event.token == token).count() == 0:
            break
    event.token = token

@sqlalchemy.event.listens_for(Event, 'after_insert')
def announce_on_zulip(mapper, conn, event):
    zulip_util.announce_event(event)

@app.route('/init')
def init_event():
    event = Event.query.filter(Event.token == request.args.get('token')).first()
    return jsonify(event.to_dict())
