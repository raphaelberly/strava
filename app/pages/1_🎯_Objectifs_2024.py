import pandas as pd
import streamlit as st

from utils import db
from utils.helpers import format_timedelta

YEAR = 2023
OBJECTIVES = {
    'run': 1200,
    'ride': 5000,
}
df = db.run_query(f"SELECT * FROM strava.activities")
df_year = df[df.start_datetime_utc.dt.year == YEAR]

st.title(f'Objectifs {YEAR}')

st.header('🏃🏼‍♂️ Course à pied')

df_year_run = df_year[df_year.type.str.lower().str.contains('run')].sort_values('start_datetime_utc', ascending=False)
total_run = df_year_run.distance.sum() / 1000

st.progress(min(total_run / OBJECTIVES["run"], 1.0))

left, center, right = st.columns(3)

with left:
    st.metric('Total annuel', f'{total_run:.0f} km')
with center:
    st.metric('Objectif', f'{OBJECTIVES["run"]} km')
with right:
    st.metric('Complétion', f'{total_run / OBJECTIVES["run"] * 100:.1f} %')

st.dataframe(
    data=pd.DataFrame({
        'Date': df_year_run.start_datetime_utc.dt.date,
        'Nom': df_year_run.name,
        'Distance (km)': (df_year_run.distance / 1000).round(2),
        'Allure (min/km)': format_timedelta(
            pd.to_timedelta((df_year_run.moving_time / 60) / (df_year_run.distance / 1000), unit='min')
        ),
        'url': 'https://www.strava.com/activities/' + df_year_run.id.astype(str),
    }).head(5),
    hide_index=True,
    use_container_width=True,
    column_config={'url': st.column_config.LinkColumn("URL Strava")},
)

st.header('🚴🏼‍♂️ Vélo de route')

df_year_ride = df_year[df_year.type.str.lower().str.contains('ride')].sort_values('start_datetime_utc', ascending=False)
total_ride = df_year_ride.distance.sum() / 1000

st.progress(min(total_ride / OBJECTIVES["ride"], 1.0))

left, center, right = st.columns(3)

with left:
    st.metric('Total annuel', f'{total_ride:.0f} km')
with center:
    st.metric('Objectif', f'{OBJECTIVES["ride"]} km')
with right:
    st.metric('Complétion', f'{total_ride / OBJECTIVES["ride"] * 100:.1f} %')

st.dataframe(pd.DataFrame({
    'Date': df_year_ride.start_datetime_utc.dt.date,
    'Nom': df_year_ride.name,
    'Distance (km)': (df_year_ride.distance / 1000).round(2),
    'Vitesse (km/h)': ((df_year_ride.distance / 1000) / (df_year_ride.moving_time / 3600)).round(1),
    'url': 'https://www.strava.com/activities/' + df_year_ride.id.astype(str),
}).head(5),
    hide_index=True,
    use_container_width=True,
    column_config={'url': st.column_config.LinkColumn("URL Strava")},
)
