import os
from urllib.parse import urlparse, quote, unquote_plus
import re

ZULIP_SITE = os.getenv('ZULIP_RSVP_SITE', 'https://recurse.zulipchat.com')


def narrow_url_to_stream_topic(url):
    parsed_url = urlparse(url)
    unquoted_fragment = unquote_plus(parsed_url.fragment.replace('.', '%'))
    split_fragment = re.split('/', unquoted_fragment)

    if len(split_fragment) < 5:
        return None, None

    stream = split_fragment[2]
    topic = split_fragment[4]
    return stream, topic


def stream_topic_to_narrow_url(stream, topic):
    quoted_stream = quote(stream, '.')
    quoted_topic = quote(topic, '.')
    fragment = ("#narrow/stream/%s/topic/%s") % (quoted_stream, quoted_topic)

    zulipped_fragment = fragment.replace('%', '.')
    url = ZULIP_SITE + zulipped_fragment

    return url
