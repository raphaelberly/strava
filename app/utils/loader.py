import streamlit as st

from utils import db

# Saves a query on every click. Activities come in hourly, and the home page's refresh button clears the cache.
DATA_TTL = 600


@st.cache_data(ttl=DATA_TTL)
def fetch_activities_df():
    # Columns the pages use: the polyline, the bulk of the table, is left out
    return db.run_query("""
        SELECT id, start_datetime_utc, type, name, distance, total_elevation_gain, moving_time
        FROM strava.activities;
    """)


@st.cache_data(ttl=DATA_TTL)
def fetch_zwift_activities_df():
    return db.run_query("SELECT * FROM strava.activities_curated WHERE ftp_base_w IS NOT NULL;")


@st.cache_data(ttl=DATA_TTL)
def fetch_laps_df():
    return db.run_query("SELECT * FROM garmin.lap_enriched WHERE activity_type IN ('running', 'trail_running');")
