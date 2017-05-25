import os

key_word = os.getenv('ZULIP_KEY_WORD', 'rsvp')

if not os.getenv('RSVPBOT_PRODUCTION', None) and key_word == 'rsvp':
    raise RuntimeError("You can't use the keyword 'rsvp' unless you're in production. Please set $ZULIP_KEY_WORD in your .env.")

zulip_username = os.environ['ZULIP_RSVP_EMAIL']
zulip_api_key = os.environ['ZULIP_RSVP_KEY']
zulip_site = os.getenv('ZULIP_RSVP_SITE', 'https://recurse.zulipchat.com')

rc_client_id = os.environ['RC_CLIENT_ID']
rc_client_secret = os.environ['RC_CLIENT_SECRET']
rc_root = os.environ['RC_ROOT']
rc_api_root = rc_root + '/api/v1'

rsvpbot_stream = os.getenv('RSVPBOT_STREAM', 'RSVPs')
rsvpbot_announce_subject = os.getenv('RSVPBOT_ANNOUNCE_SUBJECT', 'announce')
