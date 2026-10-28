import argparse
import logging
import re
from urllib.parse import parse_qs, urlparse

import yaml

from lib.logger import configure_logging
from lib.strava import Strava

# Setup logging
LOGGER = logging.getLogger(__name__)
configure_logging(logging.INFO)

# The app's "Authorization Callback Domain" (strava.com/settings/api) must be localhost
AUTHORIZE_URL = 'https://www.strava.com/oauth/authorize?client_id={client_id}&response_type=code' \
                '&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope={scope}'
# activity:read_all for "Only You" activities, activity:write for the automations of strava_webhook.py
SCOPE = 'read,activity:read_all,activity:write'


if __name__ == '__main__':

    # Create argument parser
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--secrets', '-s', type=str, help='Path to YAML file containing secrets')

    # Parse arguments
    args = parser.parse_args()
    secrets_path = args.secrets or 'conf/secrets.yaml'
    secrets = yaml.safe_load(open(secrets_path))

    # Have the athlete authorize the app in the browser, which then fails to load localhost: its URL holds the code
    LOGGER.info(AUTHORIZE_URL.format(client_id=secrets['strava']['client_id'], scope=SCOPE))
    query = parse_qs(urlparse(input('Open this URL, authorize, then paste the URL it redirects to: ')).query)
    granted = query['scope'][0].split(',')
    assert all(scope in granted for scope in SCOPE.split(',')), f'Missing scopes, only granted: {granted}'

    # Write the new refresh token in place, so that the comments of the secrets file are kept
    refresh_token = Strava(secrets['strava']).authorize(query['code'][0])['refresh_token']
    content = open(secrets_path).read()
    content, count = re.subn(r'^(  refresh_token:).*$', rf'\1 {refresh_token}', content, flags=re.MULTILINE)
    assert count == 1, f'Expected one refresh_token line in {secrets_path}, found {count}'
    open(secrets_path, 'w').write(content)
    LOGGER.info(f'Saved the new Strava refresh token in {secrets_path}')
