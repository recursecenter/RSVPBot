from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from os import environ

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recurse_id = db.Column(db.Integer, unique=True)
    token = db.Column(db.String, unique=True)

    def to_dict(self):
      return {
        'recurse_id': self.recurse_id,
        'token': self.token
      }

@app.route('/init')
def init_event():
  event = Event.query.filter_by(token=request.args.get('token')).first()
  return jsonify(event.to_dict())
