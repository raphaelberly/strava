CREATE SCHEMA trails;

-- Trail network of a zone, rebuilt as a whole by insert_trails.py.
-- One row per stretch of an OSM way with a single park marking, or per park trail missing from OSM.
CREATE TABLE trails.trail (
  zone                  VARCHAR(64)   NOT NULL,
  trail_index           INT           NOT NULL,
  source                VARCHAR(16)   NOT NULL,  -- osm or park
  osm_way_id            BIGINT,
  highway               VARCHAR(32),
  balisage              VARCHAR(128),            -- park marking colours, NULL when not marked by the park
  etiq_num              VARCHAR(16),
  length_m              FLOAT         NOT NULL,
  osm_tags              JSONB,
  geometry              TEXT          NOT NULL,  -- GeoJSON LineString, WGS84
  insert_datetime_utc   TIMESTAMP     NOT NULL,
  CONSTRAINT "trail_pkey" PRIMARY KEY (zone, trail_index)
);
