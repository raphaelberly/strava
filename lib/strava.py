import requests


class Strava(object):

    auth_url = "https://www.strava.com/oauth/token"
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    activity_url = "https://www.strava.com/api/v3/activities/{activity_id}"
    # Seconds, so that a hanging call fails the cron run instead of blocking it
    timeout = 30

    def __init__(self, credentials):
        self._credentials = credentials
        self._access_token = None

    def login(self):
        payload = {
            'client_id': self._credentials['client_id'],
            'client_secret': self._credentials['client_secret'],
            'refresh_token': self._credentials['refresh_token'],
            'grant_type': "refresh_token",
            'f': 'json'
        }
        res = requests.post(self.auth_url, data=payload, timeout=self.timeout)
        res.raise_for_status()
        self._access_token = res.json()['access_token']

    def activities(self, after=None, before=None, per_page=200, page=1):
        header = {'Authorization': f'Bearer {self._access_token}'}
        param = {'per_page': per_page, 'page': page}
        if after:
            param['after'] = after
        if before:
            param['before'] = before
        res = requests.get(self.activities_url, headers=header, params=param, timeout=self.timeout)
        res.raise_for_status()
        return res.json()

    def activity(self, activity_id):
        header = {'Authorization': f'Bearer {self._access_token}'}
        res = requests.get(self.activity_url.format(activity_id=activity_id), headers=header, timeout=self.timeout)
        res.raise_for_status()
        return res.json()
