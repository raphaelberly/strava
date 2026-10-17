CREATE SCHEMA garmin;

CREATE TABLE garmin.activity (
  id                      BIGINT        NOT NULL  UNIQUE,
  type                    VARCHAR(128)  NOT NULL,
  start_datetime_utc      TIMESTAMP     NOT NULL,
  distance                FLOAT,
  moving_time             FLOAT,
  elapsed_time            FLOAT,
  elevation_gain          FLOAT,
  elevation_loss          FLOAT,
  average_speed           FLOAT,
  max_speed               FLOAT,
  max_vertical_speed      FLOAT,
  elev_high               FLOAT,
  elev_low                FLOAT,
  average_cadence         FLOAT,
  average_heartrate       FLOAT,
  max_heartrate           FLOAT,
  average_power           FLOAT,
  max_power               FLOAT,
  calories                FLOAT,
  stride_length           FLOAT,
  vertical_oscillation    FLOAT,
  vertical_ratio          FLOAT,
  ground_contact_balance  FLOAT,
  ground_contact_time     FLOAT,
  vo2_max                 FLOAT,
  CONSTRAINT "activity_pkey" PRIMARY KEY (id)
);

CREATE TABLE garmin.lap (
  activity_id                   BIGINT    NOT NULL,
  lap_index                     INT       NOT NULL,
  distance                      FLOAT,
  moving_time                   FLOAT,
  elapsed_time                  FLOAT,
  elevation_gain                FLOAT,
  elevation_loss                FLOAT,
  average_speed                 FLOAT,
  max_speed                     FLOAT,
  max_vertical_speed            FLOAT,
  elev_high                     FLOAT,
  elev_low                      FLOAT,
  average_cadence               FLOAT,
  average_heartrate             FLOAT,
  max_heartrate                 FLOAT,
  average_power                 FLOAT,
  max_power                     FLOAT,
  calories                      FLOAT,
  stride_length                 FLOAT,
  vertical_oscillation          FLOAT,
  vertical_ratio                FLOAT,
  ground_contact_balance        FLOAT,
  ground_contact_time           FLOAT,
  CONSTRAINT "lap_pkey"             PRIMARY KEY (activity_id, lap_index),
  CONSTRAINT "lap_fkey_activity"    FOREIGN KEY (activity_id)    REFERENCES garmin.activity (id)
);

CREATE OR REPLACE VIEW garmin.activity_enriched AS (
    SELECT DISTINCT ON (g.id)
        g.*,
        s.name
    FROM garmin.activity g
    -- The Strava activity recorded at the same time, also when Garmin activities were merged into one on Strava
    -- or its type was changed there
    LEFT JOIN strava.activities s
        ON (g.start_datetime_utc, make_interval(secs => g.elapsed_time))
            OVERLAPS (s.start_datetime_utc, make_interval(secs => s.elapsed_time))
    -- A single Strava activity per Garmin one: the closest start
    ORDER BY g.id, abs(extract(epoch FROM s.start_datetime_utc - g.start_datetime_utc))
);

CREATE OR REPLACE VIEW garmin.lap_enriched AS (
    SELECT
        a.type                  AS activity_type,
        a.start_datetime_utc    AS activity_start_datetime_utc,
        a.name                  AS activity_name,
        l.*
    FROM garmin.lap l
    INNER JOIN garmin.activity_enriched a
        ON l.activity_id = a.id
);
