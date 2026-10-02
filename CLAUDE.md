# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Personal sports-data project: cron-style scripts pull activities from Strava and Garmin Connect into PostgreSQL, and a Streamlit app (French UI) analyses them. No tests, no linter, no build step. Python 3.12 (pyenv, local `.python-version` is gitignored); dependencies in `requirements.txt`.

## Commands

All root scripts read `conf/*.yaml` via relative paths, so run them from the repo root:

```bash
pip install -r requirements.txt
python insert_activities.py          # Strava -> strava.activities (upsert)
python insert_garmin_activities.py   # Garmin running activities + laps -> garmin.activity / garmin.lap
python check_activities.py           # Push alert for likely duplicate Strava activities in the last month
python garmin_login.py               # One-off: log in with email/password and dump Garmin tokens to ~/.garminconnect
```

The Streamlit app must be run from inside `app/`, because `app/utils/__init__.py` opens `../conf/secrets.yaml` and pages import `from utils import ...`:

```bash
cd app && streamlit run 📈_Accueil.py
```

## Configuration

`conf/` holds YAML files with real credentials. Never print, cat or commit them.

- `conf/secrets.yaml` (gitignored): `db` (kwargs for `Database`, including optional SSH tunnel fields `remote_host`/`remote_port`/`remote_username`/`local_port`), `strava` (OAuth refresh-token credentials), `push` (Pushover `user_key`/`api_token`), `garmin` (`email`, `password`, `token_store`).
- `conf/conf.yaml`: `columns` maps each `strava.activities` column to a dotted path in the Strava API payload (e.g. `polyline: map.summary_polyline`). `insert_activities.py` walks these paths, so adding a Strava column means adding it here and in the table.
- `conf/garmin.yaml`: `activity` and `lap` map DB columns to Garmin payload keys (flat, not dotted).
- `app/conf/objectives.yaml`: yearly objectives for the Objectifs page (sports matched by substring of lowercased `type`, `obj_type` of `dist`/`count`/`elev`, optional `name_pattern` regex and `filter_dist` in km).

## Architecture

- `lib/database.py`: `get_conn` context manager (optionally through an `sshtunnel` forwarder) and a flat `Database` class with `run_query` (returns a DataFrame), `insert`, `upsert(constraint_name=...)` and `last_activity_timestamp`. Queries are built as f-string / `.format()` SQL with `'` escaped and `'None'` replaced by `NULL`; parameterized queries are deliberately not used. `get_conn` and `lib/push.py` are copied by hand across the author's other repos (accountin, journal): keep them in sync rather than refactoring one copy.
- `lib/strava.py`: thin wrapper over the Strava REST API, one method per endpoint returning raw JSON.
- `lib/resources/*.sql`: schema DDL for `strava` and `garmin` schemas, including the views the app reads (`strava.activities_curated`, `garmin.activity_enriched`, `garmin.lap_enriched`). Apply changes manually; there is no migration tool.
- The `Database` schema is set per instance: Strava code uses `secrets['db']['schema']`, the Garmin script overrides it to `garmin`.

### Ingestion behaviour

- **Strava**: fetches pages of 200 activities after `last_activity_timestamp(offset=5)`, so the 5 most recent activities are re-fetched and re-upserted to pick up late edits. Dedup is the `activities_pkey` upsert. Special cases in `insert_activities.py`: `Run` with `sport_type == 'TrailRun'` is stored as type `TrailRun`; `VirtualRide` triggers a detail call and parses `ftp_base` from the description (`base ftp (de )?N w`); `AlpineSki`/`Snowboard` get elevation gain forced to 0.
- **Garmin**: fetches from the date of the last stored activity to today, keeps only `running` types, inserts oldest first, and skips rows on `UniqueViolation`.
- Failures send a Pushover alert (`⚠️ Strava Error`, `⚠️ Garmin Error`) and then re-raise so cron sees the failure.

### Streamlit app

- `app/📈_Accueil.py` is the home page; `app/pages/` holds numbered, emoji-prefixed pages (Streamlit multipage convention).
- `app/utils/__init__.py` creates a module-level `db`; pages query it inline at module level and filter with pandas (no caching layer). Strava pages read `strava.activities`/`activities_curated`; stride, volume and activity analysis pages read `garmin.lap_enriched`.
- `app/utils/names.py` maps Strava types to French sport labels; "Renfo" is further filtered by activity name (`hiit`/`renfo`).

### Other

- `tmp/`: scratch scripts and archived previous-year objectives, not imported by anything.
- The `trails` branch holds a paused experiment matching OSM trails in the Calanques to Strava segments (osmnx, geopandas). `cache/` (gitignored) is its osmnx HTTP cache.

## Conventions

- Code, comments, logs and commit messages in English; UI strings, page titles and push notification bodies in French. Emoji only in user-facing strings and page filenames.
- Existing scripts use `print`; the author's standard (from the accountin repo) is argparse with config-path overrides, a `LOGGER` configured by `lib/logger.py` (not present here yet: copy it from accountin), and no `main()` wrapper. Apply it to new scripts and when touching old ones.
- Use `datetime.now(UTC)` for audit timestamps.
