# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Personal sports-data project: cron-style scripts pull activities from Strava and Garmin Connect into PostgreSQL, and a Streamlit app (French UI) analyses them. No tests, no linter, no build step. Python 3.12 locally and 3.11 on the Raspberry Pi that runs it (pyenv, local `.python-version` is gitignored). Dependencies are pinned: `requirements.txt` for the scripts and `lib/`, `app/requirements.txt` (which pulls in the former with `-r`) for the app.

## Commands

All root scripts read `conf/*.yaml` via relative paths, so run them from the repo root. Locally, open the SSH tunnel to the Pi's Postgres first (`Host pi-db` in `~/.ssh/config`, documented in `conf/secrets.yaml`):

```bash
ssh -fN pi-db                        # Locally only: the Pi's Postgres on localhost:5433
pip install -r app/requirements.txt   # scripts and app; requirements.txt alone covers the scripts
python insert_activities.py          # Strava -> strava.activities (upsert)
python insert_garmin_activities.py   # Garmin running activities + laps -> garmin.activity / garmin.lap
python check_activities.py           # Push alert for likely duplicate Strava activities in the last month
python garmin_login.py               # When Garmin tokens expire: prompts for email/password/MFA, dumps tokens to garmin.token_store
```

The Streamlit app must be run from inside `app/`, because `app/utils/__init__.py` opens `../conf/secrets.yaml` and pages import `from utils import ...`:

```bash
cd app && streamlit run 📈_Accueil.py
```

`app/.streamlit/config.toml` hides error details from the browser; add `--client.showErrorDetails=full` to see them while developing.

## Configuration

`conf/` holds YAML files with real credentials. Never print, cat or commit them.

- `conf/secrets.yaml` (gitignored): `db` (kwargs for `Database`: `localhost:5433` locally, the `pi-db` tunnel's end, and `localhost:5432` on the Pi), `strava` (OAuth refresh-token credentials), `push` (Pushover `user_key`/`api_token`), `garmin` (`token_store` only: `garmin_login.py` prompts for the Garmin credentials so they are never stored).
- `conf/conf.yaml`: `columns` maps each `strava.activities` column to a dotted path in the Strava API payload (e.g. `polyline: map.summary_polyline`). `insert_activities.py` walks these paths, so adding a Strava column means adding it here and in the table.
- `conf/garmin.yaml`: `activity` and `lap` map DB columns to Garmin payload keys (flat, not dotted).
- `app/conf/accounts.yaml` (gitignored): `streamlit_authenticator` credentials and cookie settings. Same user and bcrypt-hashed password as accountin's copy, but its own cookie `name`/`key`.
- `app/.streamlit/config.toml`: no error details in the browser, viewer-only toolbar (haproxy connects from localhost, so the default `auto` mode would show developer options to everyone), no usage stats.
- `app/conf/objectives.yaml`: yearly objectives for the Objectifs page (sports matched by substring of lowercased `type`, `obj_type` of `dist`/`count`/`elev`, optional `name_pattern` regex and `filter_dist` in km).

## Architecture

- `lib/database.py`: `get_conn` context manager (a plain psycopg2 connection: the SSH tunnel used locally is OpenSSH's, configured outside the code) and a flat `Database` class with `run_query` (returns a DataFrame), `insert`, `upsert(constraint_name=...)` and `last_activity_timestamp`. Queries are built as f-string / `.format()` SQL with `'` escaped and `'None'` replaced by `NULL`; parameterized queries are deliberately not used. `get_conn` and `lib/push.py` are copied by hand across the author's other repos (accountin, journal): keep them in sync rather than refactoring one copy.
- `lib/strava.py`: thin wrapper over the Strava REST API, one method per endpoint returning raw JSON and raising on HTTP errors.
- `lib/resources/*.sql`: schema DDL for `strava` and `garmin` schemas, including the views the app reads (`strava.activities_curated`, `garmin.activity_enriched`, `garmin.lap_enriched`). Apply changes manually; there is no migration tool.
- The `Database` schema is set per instance: Strava code uses `secrets['db']['schema']`, the Garmin script overrides it to `garmin`.

### Ingestion behaviour

- **Strava**: fetches pages of 200 activities after `last_activity_timestamp(offset=5)`, so the 5 most recent activities are re-fetched and re-upserted to pick up late edits. Dedup is the `activities_pkey` upsert. Special cases in `insert_activities.py`: `Run` with `sport_type == 'TrailRun'` is stored as type `TrailRun`; `VirtualRide` triggers a detail call and parses `ftp_base` from the description (`base ftp (de )?N w`); `AlpineSki`/`Snowboard` get elevation gain forced to 0.
- **Garmin**: fetches from the date of the last stored activity to today, keeps only `running` types, inserts oldest first, and skips rows on `UniqueViolation`.
- Failures send a Pushover alert (`⚠️ Strava Error`, `⚠️ Garmin Error`) and then re-raise so cron sees the failure.

### Streamlit app

- `app/📈_Accueil.py` is the home page; `app/pages/` holds numbered, emoji-prefixed pages (Streamlit multipage convention). Cross-page buttons use `st.switch_page('pages/<filename>')`.
- Every page calls `authenticate()` from `app/autenthicator.py` before querying anything; a new page must too, since Streamlit serves each page at its own URL. The module is copied from accountin (keep both in sync). It writes form logins to `log/app_logins.log` (path relative to `app/`) with the client IP from the last `X-Forwarded-For` header, the one the Pi's haproxy adds. On the Pi, fail2ban's `sports-login` jail bans IPs from `Failed login from <ip>` lines, using accountin's `/etc/fail2ban/filter.d/accountin-login.conf` filter, so changing that message breaks banning silently.
- `app/utils/__init__.py` creates a module-level `db`; pages query it inline at module level and filter with pandas (no caching layer). Strava pages read `strava.activities`/`activities_curated`; stride, volume and activity analysis pages read `garmin.lap_enriched`.
- `app/utils/names.py` maps Strava types to French sport labels; "Renfo" is further filtered by activity name (`hiit`/`renfo`).

### Deployment (Raspberry Pi)

- The repo is cloned in `/home/pi/strava` and runs from the `stravaenv3.11.6` pyenv virtualenv, for both cron and the app. Python 3.11 is why `garminconnect` stays on 0.2.x (0.3.3+ needs 3.12 and replaces the garth tokens).
- Cron runs `insert_activities.py`, `check_activities.py` and `insert_garmin_activities.py` hourly from 8:00 to 23:00, logging to `log/<script>.log`.
- Supervisor's `healthnsports` program serves the app on `127.0.0.1:8091`; haproxy exposes it as `sports.rberly.ovh`, with per-IP rate limits shared with the other apps.

### Other

- `tmp/`: scratch scripts and archived previous-year objectives, not imported by anything.
- The `trails` branch holds a paused experiment matching OSM trails in the Calanques to Strava segments (osmnx, geopandas). `cache/` (gitignored) is its osmnx HTTP cache.

## Conventions

- Code, comments, logs and commit messages in English; UI strings, page titles and push notification bodies in French. Emoji only in user-facing strings and page filenames.
- Existing scripts use `print`; the author's standard (from the accountin repo) is argparse with config-path overrides, a `LOGGER` configured by `lib/logger.py` (copied from accountin), and no `main()` wrapper (see `garmin_login.py`). Apply it to new scripts and when touching old ones.
- Use `datetime.now(UTC)` for audit timestamps.
