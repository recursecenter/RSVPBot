import os
import zulip

import config
import strings


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
            title=event.title,
            url=event.url,
            timestamp=event.timestamp(),
            created_by=event.created_by
        )
    })
