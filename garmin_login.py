import argparse
import logging
import os
from getpass import getpass

import garminconnect
import yaml

from lib.logger import configure_logging

# Configure logging
configure_logging(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Create argument parser
parser = argparse.ArgumentParser(add_help=True)
parser.add_argument('--secrets', '-s', type=str, help='Path to YAML file containing secrets')

# Parse arguments & load secrets file
args = parser.parse_args()
token_store = os.path.expanduser(yaml.safe_load(open(args.secrets or 'conf/secrets.yaml'))['garmin']['token_store'])

# Log in, prompting for credentials so that they are never stored next to the tokens
garmin = garminconnect.Garmin(
    email=input('Garmin email: '),
    password=getpass('Garmin password: '),
    prompt_mfa=lambda: input('Garmin MFA code: '),
)
garmin.login()

# Save tokens where insert_garmin_activities.py reads them (dump makes them readable by the owner only)
garmin.client.dump(token_store)
LOGGER.info(f'Saved Garmin tokens to {token_store}')
