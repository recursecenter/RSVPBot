import os
import zulip

import config
import strings
import util


def make_client():
    return zulip.Client(
        config.zulip_username,
        config.zulip_api_key,
        site=config.zulip_site
    )

def announce_event(event):
    client = make_client()
    client.send_message({
        "type": "stream",
        "to": config.rsvpbot_stream,
        "subject": config.rsvpbot_announce_subject,
        "content": strings.ANNOUNCE_MESSAGE.format(
            key_word=config.key_word,
            title=event.title,
            url=event.url,
            timestamp=event.timestamp(),
            created_by=event.created_by
        )
    })

def get_names(ids):
    client = make_client()
    all_users = client.get_members()['members']
    name_mapping = {user['user_id']: user['full_name'] for user in all_users}
    return [name_mapping[id] for id in ids]


def send_message(msg, client=None):
    """Sends a message to zulip stream or user."""
    if client is None:
        client = make_client()

    msg_to = msg['display_recipient']
    if msg['type'] == 'private':
        msg_to = msg.get('sender_email') or msg_to

    client.send_message({
        "type": msg['type'],
        "subject": msg["subject"],
        "to": msg_to,
        "content": msg['body']
    })

stream_topic_to_narrow_url = util.stream_topic_to_narrow_url
