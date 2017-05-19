import requests
import json

import config

class RCClientError(Exception):
    pass

class Client:
    def __init__(self, id=config.rc_client_id, secret=config.rc_client_secret, api_root=config.rc_api_root):
        self.id = id
        self.secret = secret
        self.api_root = api_root

    def get_event(self, id, include_participants=False):
        r = self.get("events/{}".format(id), params={'include_participants': include_participants})

        if r.status_code == 404:
            return None

        return r.json()

    def get_events(self, created_at_or_after=None, ids=None):
        params = {}

        if created_at_or_after:
            params['created_at_or_after'] = created_at_or_after.isoformat()

        if ids:
            params['ids'] = json.dumps(ids)

        return self.get('events', params=params).json()

    def join(self, event_id, zulip_id):
        return self.post_as_user('events/{}/join'.format(event_id), zulip_id).json()

    def leave(self, event_id, zulip_id):
        return self.post_as_user('events/{}/leave'.format(event_id), zulip_id).json()

    def update_event(self, event_id, updates):
        return self.patch('events/{}'.format(event_id), data={'event': updates}).json()

    def post_as_user(self, path, zulip_id):
        auth = (self.id, self.secret)
        url = self.api_root + '/' + path

        r = requests.post(url, auth=auth, data={'user_param': 'zulip_id', 'user_param_value': zulip_id})

        if r.status_code != 200:
            raise RCClientError

        return r

    def get(self, path, params={}):
        auth = (self.id, self.secret)
        url = self.api_root + '/' + path

        return requests.get(url, params=params, auth=auth)

    def patch(self, path, data={}):
        auth = (self.id, self.secret)
        url = self.api_root + '/' + path

        print('data', data)
        return requests.patch(url, json=data, auth=auth)

def get_event(id, **kwargs):
    return Client().get_event(id, **kwargs)

def get_events(**kwargs):
    return Client().get_events(**kwargs)

def join(event_id, zulip_id):
    return Client().join(event_id, zulip_id)

def leave(event_id, zulip_id):
    return Client().leave(event_id, zulip_id)

def update_event(event_id, updates):
    return Client().update_event(event_id, updates)
