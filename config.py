import os

key_word = os.getenv('ZULIP_KEY_WORD', 'rsvp')

zulip_username = os.environ['ZULIP_RSVP_EMAIL']
zulip_api_key = os.environ['ZULIP_RSVP_KEY']
zulip_site = os.getenv('ZULIP_RSVP_SITE', 'https://recurse.zulipchat.com')

rc_client_id = os.environ['RC_CLIENT_ID']
rc_client_secret = os.environ['RC_CLIENT_SECRET']
rc_api_root = os.environ['RC_API_ROOT']

rsvpbot_stream = os.getenv('RSVPBOT_STREAM', 'events')
rsvpbot_announce_subject = os.getenv('RSVPBOT_ANNOUNCE_SUBJECT', 'announce')
