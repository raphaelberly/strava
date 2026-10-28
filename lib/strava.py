import re
from datetime import datetime, UTC

import requests


class Strava(object):

    auth_url = "https://www.strava.com/oauth/token"
    athlete_url = "https://www.strava.com/api/v3/athlete"
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    activity_url = "https://www.strava.com/api/v3/activities/{activity_id}"
    subscriptions_url = "https://www.strava.com/api/v3/push_subscriptions"
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

    # Exchange the code of an authorization (see strava_login.py) for the athlete's tokens
    def authorize(self, code):
        payload = {
            'client_id': self._credentials['client_id'],
            'client_secret': self._credentials['client_secret'],
            'code': code,
            'grant_type': 'authorization_code',
        }
        res = requests.post(self.auth_url, data=payload, timeout=self.timeout)
        res.raise_for_status()
        return res.json()

    def athlete(self):
        header = {'Authorization': f'Bearer {self._access_token}'}
        res = requests.get(self.athlete_url, headers=header, timeout=self.timeout)
        res.raise_for_status()
        return res.json()

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

    # Needs the activity:write scope
    def update_activity(self, activity_id, **fields):
        header = {'Authorization': f'Bearer {self._access_token}'}
        res = requests.put(self.activity_url.format(activity_id=activity_id), headers=header, json=fields,
                           timeout=self.timeout)
        res.raise_for_status()
        return res.json()

    # Webhook subscriptions are the app's, authenticated with its client credentials rather than an athlete token
    def subscriptions(self):
        param = {'client_id': self._credentials['client_id'], 'client_secret': self._credentials['client_secret']}
        res = requests.get(self.subscriptions_url, params=param, timeout=self.timeout)
        res.raise_for_status()
        return res.json()

    def create_subscription(self, callback_url):
        payload = {
            'client_id': self._credentials['client_id'],
            'client_secret': self._credentials['client_secret'],
            'callback_url': callback_url,
            'verify_token': self._credentials['verify_token'],
        }
        res = requests.post(self.subscriptions_url, data=payload, timeout=self.timeout)
        res.raise_for_status()
        return res.json()

    def delete_subscription(self, subscription_id):
        param = {'client_id': self._credentials['client_id'], 'client_secret': self._credentials['client_secret']}
        res = requests.delete(f'{self.subscriptions_url}/{subscription_id}', params=param, timeout=self.timeout)
        res.raise_for_status()


# Build the strava.activities row of an activity, following the column paths of conf/conf.yaml
def activity_row(raw_activity, columns):
    activity = {'update_datetime_utc': datetime.now(UTC)}
    if raw_activity['type'] == 'Run':
        if raw_activity['sport_type'] == 'TrailRun':
            raw_activity['type'] = 'TrailRun'
    # Virtual rides get a "ftp_base" field from their description, only in the detailed activity
    elif raw_activity['type'] == 'VirtualRide':
        ftp_search = re.search(r'base ftp (de )?(\d+) ?w', raw_activity.get('description') or '', re.IGNORECASE)
        if ftp_search:
            raw_activity['ftp_base'] = ftp_search.group(2)
    if raw_activity['type'] in ['AlpineSki', 'Snowboard']:
        raw_activity['total_elevation_gain'] = 0
    for column_name, column_path in columns.items():
        # Dive into nested dictionary following the provided path
        value = raw_activity
        for key in column_path.split('.'):
            value = value.get(key, {})
        if value != {} and value != '':
            activity[column_name] = value
    return activity
