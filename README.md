RSVPBot
=======
[![Build Status](https://travis-ci.org/kokeshii/RSVPBot.svg?branch=master)](https://travis-ci.org/kokeshii/RSVPBot)

This is a simple Zulip bot that converts a Zulip conversation into an event context.
People can then use simple commands to rsvp to an event, set the hour, time, place, and easily ping every person who RSVP'ed.

## Contributing

* Make your pull requests to the `dev` branch
* Write tests for any new command or feature introduced
* Make sure the requirements.txt file is kept up to date
* Make sure any new messages that the bot sends publicly or privately follow the [RC Social Rules](https://www.recurse.com/manual#sub-sec-social-rules). It takes a village, people!
* New features are TOTALLY AWESOME, but RSVPBot has a few [open issues](https://github.com/kokeshii/RSVPBot/issues) you can take a look at if you want to get familiarized with the code or you're looking for ideas on how to contribute.
* HAVE FUN PEOPLE YAY

## Environment Variables

```
# Required
export ZULIP_RSVP_EMAIL="<bot-email>"
export ZULIP_RSVP_KEY="<bot-key>"

# Optional
export ZULIP_RSVP_SITE="https://your-zulip-site.com"  # default is https://recurse.zulipchat.com
export ZULIP_KEY_WORD="rsvp"                          # default is rsvp
```

## Running
First, make sure python requirements are installed:

`pip install -r requirements.txt`

Then, to run the bot:

`python bot.py`


## Testing
`
python tests.py
`

## Commands
**Command**|**Description**
--- | ---
**`rsvp yes`**|Marks **you** as attending this event.
**`rsvp no`**|Marks you as **not** attending this event.
`rsvp init https://www.recurse.com/calendar/:id`|Initializes a thread as an RSVPBot event. Must be used before most other commands.
`rsvp help`|Shows this handy table.
`rsvp ping`|Pings everyone that has RSVP'd so far.
`rsvp summary`|Displays a summary of this event, including the description, and list of attendees.
`rsvp move <destination_url>`|Moves this event to another stream/topic. Requires full URL for the destination (e.g.'https://zulip.com/#narrow/stream/announce/topic/All.20Hands.20Meeting') (can only be called by the caller of `rsvp init`)
`rsvp credits`|Lists all the awesome people that made RSVPBot a reality.
