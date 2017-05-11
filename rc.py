import requests


class Client:
    def __init__(self, id, secret, api_root='https://www.recurse.com/api/v1'):
        self.id = id
        self.secret = secret
        self.api_root = api_root

    def get_events(self):
        return self.get('events', params={'created_at_or_after': '5/10/17'})

    def get(self, path, params={}):
        auth = (self.id, self.secret)
        url = self.api_root + '/' + path

        return requests.get(url, params=params, auth=auth).json()
