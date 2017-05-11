import requests

from os import environ


class Client:
    def __init__(self, id=environ['RC_CLIENT_ID'], secret=environ['RC_CLIENT_SECRET'], api_root=environ['RC_API_ROOT']):
        self.id = id
        self.secret = secret
        self.api_root = api_root

    def get_events(self):
        return self.get('events', params={'created_at_or_after': '5/10/17'})

    def get(self, path, params={}):
        auth = (self.id, self.secret)
        url = self.api_root + '/' + path

        return requests.get(url, params=params, auth=auth).json()
