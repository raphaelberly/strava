import re

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
last_epoch = db.last_activity_timestamp()
raw_activities = []
per_page = 200
page = 1
while True:  # Load pages sequentially
    response = strava.activities(**({'after': last_epoch} if last_epoch is not None else {}), per_page=per_page, page=page)
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
    activity = {}
    # For virtual rides, fetch description & create new "ftp_base" field
    if raw_activity['type'] == 'VirtualRide':
        raw_activity = strava.activity(raw_activity['id'])
        ftp_search = re.search(r'base ftp (de )?(\d+) ?w', raw_activity['description'], re.IGNORECASE)
        if ftp_search:
            raw_activity['ftp_base'] = ftp_search.group(2)
    if raw_activity['type'] in ['AlpineSki', 'Snowboard']:
        raw_activity['total_elevation_gain'] = 0
    for column_name, column_path in conf['columns'].items():
        # Dive into nested dictionary following the provided path
        value = raw_activity
        for key in column_path.split('.'):
            value = value.get(key, {})
        if value != {} and value != '':
            activity[column_name] = value
    # Insert activity
    db.insert('activities', **activity)
    i += 1
if i > 0:
    print(f'Successfully inserted {i} new activities to database')
