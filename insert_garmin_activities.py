from datetime import date, timedelta, datetime

import garminconnect
import yaml
from psycopg2.errors import UniqueViolation
from lib.database import Database

# Read configuration files
conf = yaml.safe_load(open('conf/garmin.yaml'))
secrets = yaml.safe_load(open('conf/secrets.yaml'))
secrets['db']['schema'] = 'garmin'

# Configure database connector
db = Database(**secrets['db'])

tokenstore = "~/.garminconnect"
garmin = garminconnect.Garmin()
garmin.login(tokenstore)

start_date = date.fromtimestamp(db.last_activity_timestamp(table_name='activity')).isoformat()

# RUNNING
i, j = 0, 0
activities = garmin.get_activities_by_date(start_date, date.today().isoformat())
for activity in activities:
    if 'running' in activity['activityType']['typeKey']:
        try:
            # Insert activity
            db.insert(
                'activity',
                type=activity['activityType']['typeKey'],
                **{k: activity.get(v) for k, v in conf['activity'].items()}
            )
            i += 1
            # Insert laps
            laps = garmin.get_activity_splits(activity['activityId'])['lapDTOs']
            for lap in laps:
                db.insert(
                    'lap',
                    activity_id=activity['activityId'],
                    activity_start_datetime_utc=activity['startTimeGMT'],
                    ** {k: lap.get(v) for k, v in conf['lap'].items()}
                )
                j += 1
        except UniqueViolation:
            break

print(f'Inserted {i} activities and {j} laps to database')
