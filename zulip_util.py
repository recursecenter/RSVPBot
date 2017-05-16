import os
import zulip

import config


def make_client():
    return zulip.Client(
        config.zulip_username,
        config.zulip_api_key,
        site=config.zulip_site
    )

def announce_event(event):
    client = None
