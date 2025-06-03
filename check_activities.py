import yaml

from lib.database import Database
from lib.push import Push

# Read configuration files
secrets = yaml.safe_load(open('conf/secrets.yaml'))

# Configure notification service
push = Push(**secrets['push'])

# Configure database connector
db = Database(**secrets['db'])

query = """
WITH
activity_lags AS (
    SELECT
        a.name,
        lag(a.name) OVER (ORDER BY a.start_datetime_utc) AS lag_name,
        a.type,
        lag(a.type) OVER (ORDER BY a.start_datetime_utc) AS lag_type,
        date_trunc('hour', a.start_datetime_utc) AS date,
        lag(date_trunc('hour', a.start_datetime_utc)) OVER (ORDER BY a.start_datetime_utc) AS lag_date
    FROM strava.activities a
)
SELECT name, lag_name
FROM activity_lags a
WHERE a.type = a.lag_type
    AND a.date = a.lag_date
    AND date(date) >= date(current_date) - INTERVAL '1' MONTH
"""
results = db.run_query(query)
if len(results) > 0:
    print(f'{len(results)} potential duplicates found')
    for item in results.to_dict(orient="records"):
        push.send_message(
            message=f'''Similar activities found: "{item['name']}" and "{item['lag_name']}"''',
            title="⚠️ Potential Strava duplicates"
        )
else:
    print('No potential duplicates found')
