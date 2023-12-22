from datetime import date, timedelta

import garminconnect
import yaml

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

target_date = (date.today() - timedelta(days=1)).isoformat()

# RUNNING
i, j = 0, 0
activities = garmin.get_activities_by_date('2023-10-25', target_date)
for activity in activities:
    if 'running' in activity['activityType']['typeKey']:
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

print(f'Inserted {i} activities and {j} laps to database')
