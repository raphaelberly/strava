from datetime import date

import garminconnect
import yaml
from psycopg2.errors import UniqueViolation
from tqdm import tqdm

from lib.database import Database
from lib.push import Push

# Read configuration files
conf = yaml.safe_load(open('conf/garmin.yaml'))
secrets = yaml.safe_load(open('conf/secrets.yaml'))
secrets['db']['schema'] = 'garmin'

# Configure database connector
db = Database(**secrets['db'])

# Configure notification service
push = Push(**secrets['push'])


try:
    garmin = garminconnect.Garmin()
    garmin.login(secrets['garmin']['token_store'])
except Exception as e:
    push.send_message("Could not connect to Garmin", title='⚠️ Garmin Error')
    raise e

start_date = date.fromtimestamp(db.last_activity_timestamp(table_name='activity')).isoformat()

# RUNNING
i, j = 0, 0
activities = garmin.get_activities_by_date(start_date, date.today().isoformat())

# Read from oldest to newest, and show progress bar if more than one candidate activity
activities_gen = tqdm(reversed(activities), total=len(activities)) if len(activities) > 1 else reversed(activities)
for activity in activities_gen:
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
                    ** {k: lap.get(v) for k, v in conf['lap'].items()}
                )
                j += 1
        except UniqueViolation:
            continue
        except Exception as e:
            push.send_message("Could not insert Garmin activities", title='⚠️ Garmin Error')
            raise e

print(f'Inserted {i} activities and {j} laps to database')
