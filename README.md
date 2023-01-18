RSVPBot
=======

This is a Zulip bot that integrates with the [Recurse Center calendar](https://www.recurse.com/calendar). The original version which works independently of the RC calendar and includes Google Calendar integration can be found at [kokeshii/RSVPBot](https://github.com/kokeshii/RSVPBot).

RSVPBot lets you associate a Zulip thread with an RC calendar event, and lets people RSVP to the event directly from Zulip.

## Contributing

* Write tests for any new command or feature introduced
* Make sure the requirements.txt file is kept up to date
* New features are TOTALLY AWESOME, but you can take a loot at [open issues](https://github.com/recursecenter/RSVPBot/issues) to get familiarized with the code or if you're looking for ideas on how to contribute.
* HAVE FUN PEOPLE YAY

## Requirements

* PostgreSQL
* [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
* Python 3.11

## Running

This bot uses Python 3 and is built to be deployed on Heroku. RSVPBot will automatically load any environment variables you set in a file called `.env` in the root of your local repo:

```
DATABASE_URL=postgres://localhost/rsvpbot
PYTHONUNBUFFERED=true

ZULIP_RSVP_EMAIL=your-test-rsvp-bot@recurse.zulipchat.com
ZULIP_RSVP_KEY=YOUR_API_KEY
ZULIP_RSVP_SITE=https://recurse.zulipchat.com

ZULIP_KEY_WORD=rsvptest

RC_CLIENT_ID=fake-client-id
RC_CLIENT_SECRET=fake-client-secret
RC_ROOT=http://localhost:5000

RSVPBOT_STREAM=bot-test
RSVPBOT_ANNOUNCE_SUBJECT="My RSVPBot testing announce"
```

### One-time setup

```
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

createdb rsvpbot

# Runs migrations. See `alembic help` for more info.
alembic upgrade head
```

### Running the code

The `heroku` commands load environmental variables from your `.env` file. (You can learn more [here](https://devcenter.heroku.com/articles/heroku-cli).)

```
# To start the bot locally (see Procfile)
heroku local

# To run the tests
python tests.py
```

### Developing without API access

RSVPBot relies on a special permission in the recurse.com API that lets it access events and RSVP on behalf of any user. This makes it hard for someone without access to the recurse.com codebase to work on RSVPBot.

To get around this problem, we've built a "dev server" that you can run locally that mimics the recurse.com events API. You can find the dev server in the devserver folder. The example `.env` file above is configured to work with the dev server.

To run the dev server:

```
python devserver/__init__.py
```

To run the dev server with a different port:

```
PORT=12345 python devserver/__init__.py
```

If you are making changes to RSVPBot that require changes to the API, make those changes in the devserver and include them as part of your PR. Once the feature is settled and the code has been reviewed, we'll make the same API changes on recurse.com and then merge and deploy your PR.

To have the dev server reload itself every time you change its source:

```
FLASK_DEBUG=1 python devserver/__init__.py
```

**WARNING**: If you use FLASK_DEBUG=1, the dev server state will be reset every time you change the code. When this happens, you may have to clean out the events in your database:

```
echo 'DELETE FROM events;' | psql rsvpbot
```

If you load the dev server index in your browser, you can see the current state, create new events, and reset the state.

### Specifying users

The dev server has a hardcoded set of users. When you specify a user (for the join and leave api endpoints), the dev server will ignore the Zulip ID of the users and return a user for any Zulip ID you specify. For any specified Zulip ID, the same user will always be returned. This can make the effects of `rsvptest yes` and `rsvptest no` a bit confusing.

## Commands
**Command**|**Description**
--- | ---
**`rsvp yes`**|Marks **you** as attending this event.
**`rsvp no`**|Marks you as **not** attending this event.
`rsvp init`|Create a new event on the RC calendar that will be tracked in the thread you're in.
`rsvp init https://www.recurse.com/calendar/:id`|Initializes a thread as an RSVPBot event using an existing RC calendar event. Must be used before most other commands.
`rsvp help`|Shows this handy table.
`rsvp ping`|Pings everyone that has RSVP'd so far.
`rsvp summary`|Displays a summary of this event, including the description, and list of attendees.
`rsvp move <destination_url>`|Moves this event to another stream/topic. Requires full URL for the destination (e.g.'https://zulip.com/#narrow/stream/announce/topic/All.20Hands.20Meeting')
`rsvp credits`|Lists all the awesome people that made RSVPBot a reality.
