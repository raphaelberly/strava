import yaml

from lib.database import Database
from lib.strava import Strava

# Read configuration files
secrets = yaml.safe_load(open('conf/secrets.yaml'))
conf = yaml.safe_load(open('conf/conf.yaml'))

# Configure Strava connector
strava = Strava(secrets['strava'])
strava.login()
print('Successfully connected to Strava')

# Configure database connector
db = Database(**secrets['db'])

# Fetch Strava activities
last_epoch = db.last_activity_timestamp
raw_activities = strava.activities(**({'after': last_epoch} if last_epoch is not None else {}))
if len(raw_activities) == 0:
    print('No activity to be fetched')
else:
    print(f'Successfully fetched {len(raw_activities)} activities from Strava')

# Insert activities in database one by one
i = 0
for raw_activity in raw_activities:
    activity = {}
    for column_path, column_name in conf['columns'].items():
        # Dive into nested dictionary following the provided path
        value = raw_activity
        for key in column_path.split('.'):
            value = value.get(key, {})
        if value != {}:
            activity[column_name] = value
    # Insert activity
    db.insert('activities', **activity)
    i += 1
if i > 0:
    print(f'Successfully inserted {i} new activities to database')
