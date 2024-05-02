CREATE SCHEMA strava;

CREATE TABLE strava.activities (
  id                    BIGINT          NOT NULL  UNIQUE,
  start_datetime_utc    TIMESTAMP       NOT NULL,
  type                  VARCHAR(32)     NOT NULL,
  name                  VARCHAR(256)    NOT NULL,
  distance              FLOAT,
  total_elevation_gain  FLOAT,
  moving_time           FLOAT,
  elapsed_time          FLOAT,
  average_speed         FLOAT,
  max_speed             FLOAT,
  elev_high             FLOAT,
  elev_low              FLOAT,
  average_cadence       FLOAT,
  average_heartrate     FLOAT,
  max_heartrate         FLOAT,
  average_temp          FLOAT,
  average_watts         FLOAT,
  relative_effort       FLOAT,
  ftp_base              INT,
  polyline              VARCHAR(16384)
);

CREATE VIEW strava.activities_curated AS (
  SELECT
    id,
    type,
    name,
    DATE(a.start_datetime_utc)  AS start_date,
    a.distance / 1000           AS distance_km,
    a.moving_time               AS moving_time_s,
    a.elapsed_time              AS elapsed_time_s,
    a.total_elevation_gain      AS elevatin_gain_m,
    a.average_speed * 3.6       AS speed_kph,
    a.average_cadence           AS cadence_rpm,
    a.average_heartrate         AS heartrate_bpm,
    a.max_heartrate             AS max_heartrate_bpm,
    a.average_watts             AS average_power_w,
    a.ftp_base                  AS ftp_base_w,
    a.relative_effort           AS relative_effort
  FROM strava.activities a
);
