CREATE SCHEMA strava;

CREATE TABLE strava.activities (
  id                    BIGINT          NOT NULL  UNIQUE,
  start_date_utc        TIMESTAMP       NOT NULL,
  type                  VARCHAR(32)     NOT NULL,
  name                  VARCHAR(256)    NOT NULL,
  distance              FLOAT           NOT NULL,
  total_elevation_gain  FLOAT           NOT NULL,
  moving_time           FLOAT           NOT NULL,
  elapsed_time          FLOAT           NOT NULL,
  average_speed         FLOAT           NOT NULL,
  max_speed             FLOAT           NOT NULL,
  elev_high             FLOAT           NOT NULL,
  elev_low              FLOAT           NOT NULL,
  average_cadence       FLOAT,
  average_heartrate     FLOAT,
  average_temp          FLOAT,
  average_watts         FLOAT,
  polyline              VARCHAR(16384)  NOT NULL
);
