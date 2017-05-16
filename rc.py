import requests

import config


class Client:
    def __init__(self, id=config.rc_client_id, secret=config.rc_client_secret, api_root=config.rc_api_root):
        self.id = id
        self.secret = secret
        self.api_root = api_root

    def get_events(self, created_at_or_after):
        return self.get('events', params={'created_at_or_after': created_at_or_after.isoformat()})

    def get(self, path, params={}):
        auth = (self.id, self.secret)
        url = self.api_root + '/' + path

        return requests.get(url, params=params, auth=auth).json()
