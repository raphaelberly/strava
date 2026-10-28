import yaml

from lib.database import Database
from lib.push import Push
from lib.strava import Strava, activity_row

# Read configuration files
secrets = yaml.safe_load(open('conf/secrets.yaml'))
conf = yaml.safe_load(open('conf/conf.yaml'))

# Configure notification service
push = Push(**secrets['push'])

try:

    # Configure Strava connector
    strava = Strava(secrets['strava'])
    strava.login()
    print('Successfully connected to Strava')

    # Configure database connector
    db = Database(**secrets['db'])

    # Fetch Strava activities
    last_epoch = db.last_activity_timestamp(offset=5)
    raw_activities = []
    per_page = 200
    page = 1
    while True:  # Load pages sequentially
        response = strava.activities(
            **({'after': last_epoch} if last_epoch is not None else {}),
            per_page=per_page,
            page=page
        )
        raw_activities.extend(response)
        if len(response) == per_page:
            page += 1
        else:
            break
    if len(raw_activities) == 0:
        print('No activity to be fetched')
    else:
        print(f'Found {len(raw_activities)} activities in Strava')

    # Insert activities in database one by one
    i = 0
    for raw_activity in raw_activities:
        # For virtual rides, fetch the detailed activity to read the FTP base from its description
        if raw_activity['type'] == 'VirtualRide':
            raw_activity = strava.activity(raw_activity['id'])
        activity = activity_row(raw_activity, conf['columns'])
        # Insert activity
        db.upsert(table_name='activities', constraint_name='activities_pkey', **activity)
        i += 1
    if i > 0:
        print(f'Successfully upserted {i} activities to database')

except Exception as e:
    push.send_message(message="Could not insert Strava activities", title="⚠️ Strava Error")
    raise e
