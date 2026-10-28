import argparse
import logging

import yaml

from lib.logger import configure_logging
from lib.strava import Strava

# Setup logging
LOGGER = logging.getLogger(__name__)
configure_logging(logging.INFO)


if __name__ == '__main__':

    # Create argument parser
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--secrets', '-s', type=str, help='Path to YAML file containing secrets')
    parser.add_argument('--create', '-c', type=str, metavar='CALLBACK_URL',
                        help='Subscribe this URL to the events, once strava_webhook.py answers on it')
    parser.add_argument('--delete', '-d', action='store_true', help='Delete the existing subscription')

    # Parse arguments
    args = parser.parse_args()

    # Load configuration files
    secrets = yaml.safe_load(open(args.secrets or 'conf/secrets.yaml'))
    strava = Strava(secrets['strava'])

    # An app has one subscription at most
    if args.delete:
        for subscription in strava.subscriptions():
            strava.delete_subscription(subscription['id'])
            LOGGER.info(f'Deleted subscription {subscription["id"]}')
    if args.create:
        # Strava calls the callback URL to validate it before answering
        LOGGER.info(f'Created subscription {strava.create_subscription(args.create)["id"]}')

    LOGGER.info(f'Subscriptions: {strava.subscriptions()}')
