import argparse
import logging

import uvicorn
import yaml
from requests import HTTPError
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from lib.database import Database
from lib.logger import configure_logging
from lib.push import Push
from lib.strava import Strava, activity_row

# Setup logging
LOGGER = logging.getLogger(__name__)
configure_logging(logging.INFO)

# haproxy routes this path of sports.rberly.ovh here as it is
WEBHOOK_PATH = '/strava/webhook'


# Answer the check Strava makes when the subscription is created
async def validate(request):
    params = request.query_params
    if params.get('hub.mode') == 'subscribe' and params.get('hub.verify_token') == secrets['strava']['verify_token']:
        return JSONResponse({'hub.challenge': params.get('hub.challenge')})
    LOGGER.warning(f'Rejected subscription validation: {dict(params)}')
    return Response(status_code=403)


# Strava wants a 200 within 2 seconds: the event is processed after the answer is sent
async def receive(request):
    event = await request.json()
    LOGGER.info(f'Received event: {event}')
    return Response(background=BackgroundTask(process_event, event))


# Strava signs nothing, so events are only hints: the activity is always read back from Strava
def process_event(event):
    if event.get('object_type') != 'activity':
        return
    activity_id = int(event['object_id'])
    try:
        # Logging in on every event saves tracking the 6-hour expiry of the access token
        strava.login()
        if event['aspect_type'] == 'delete':
            try:
                strava.activity(activity_id)
                LOGGER.warning(f'Activity {activity_id} still exists on Strava: not deleted')
                return
            except HTTPError as e:
                if e.response.status_code != 404:
                    raise e
            db.delete(table_name='activities', id=activity_id)
            LOGGER.info(f'Deleted activity {activity_id}')
        else:
            # Create and update events alike: the whole row is upserted, whatever was edited
            raw_activity = strava.activity(activity_id)
            if raw_activity['athlete']['id'] != athlete_id:
                LOGGER.warning(f'Activity {activity_id} belongs to athlete {raw_activity["athlete"]["id"]}: skipped')
                return
            activity = activity_row(raw_activity, conf['columns'])
            db.upsert(table_name='activities', constraint_name='activities_pkey', **activity)
            LOGGER.info(f'Upserted activity {activity_id} ({event["aspect_type"]})')
    except Exception as e:
        LOGGER.error(str(e))
        push.send_message(message=f"Could not process the Strava event of activity {activity_id}",
                          title="⚠️ Strava Error")
        raise e


app = Starlette(routes=[
    Route(WEBHOOK_PATH, validate, methods=['GET']),
    Route(WEBHOOK_PATH, receive, methods=['POST']),
])


if __name__ == '__main__':

    # Create argument parser
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--secrets', '-s', type=str, help='Path to YAML file containing secrets')
    parser.add_argument('--conf', '-c', type=str, help='Path to YAML file containing the column mapping')
    parser.add_argument('--port', '-p', type=int, default=8092, help='Port to listen to, on localhost')

    # Parse arguments
    args = parser.parse_args()

    # Load configuration files, read by the handlers above
    secrets = yaml.safe_load(open(args.secrets or 'conf/secrets.yaml'))
    conf = yaml.safe_load(open(args.conf or 'conf/conf.yaml'))

    # Configure connectors
    push = Push(**secrets['push'])
    db = Database(**secrets['db'])
    strava = Strava(secrets['strava'])
    strava.login()
    athlete_id = strava.athlete()['id']
    LOGGER.info(f'Connected to Strava as athlete {athlete_id}')

    # Without a log config of its own, uvicorn logs through the root logger set up above
    uvicorn.run(app, host='127.0.0.1', port=args.port, log_config=None)
