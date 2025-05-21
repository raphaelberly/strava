import numpy as np
import plotly.graph_objs as go
import streamlit as st

from utils import db


def normalize_text(text: str) -> str:
    return ' '.join(text.split('_')).capitalize()

def calculate_pace(speed_in_mps: float) -> float:
    return 1000 / speed_in_mps

def format_pace(seconds_per_km):
    minutes = seconds_per_km // 60
    seconds = seconds_per_km % 60
    return f"{int(minutes)}'{int(seconds):02d}/km"

def format_duration(seconds):
    minutes = seconds // 60
    seconds = seconds % 60
    return f'{f"{int(minutes):02d}min " if int(minutes) > 0 else ""}{int(seconds):02d}s'


laps = db.run_query("SELECT * FROM garmin.lap_enriched WHERE activity_type IN ('running', 'trail_running')")
laps.rename(columns={'activity_start_datetime_utc': 'activity_date'}, inplace=True)
laps = laps[laps['moving_time'] >= 20]
laps['max_pace'] = laps['max_speed'].apply(calculate_pace)
laps['average_pace'] = laps['average_speed'].apply(calculate_pace)

st.title('Analyse de volume 🧘🏼')

left, center, _ = st.columns(3)

years = sorted(list(set(laps['activity_date'].dt.year)))
with left:
    start_year = st.selectbox(label='Année 1', options=years, index=0)
with center:
    end_years = [y for y in years if y >= start_year]
    end_year = st.selectbox(label='Année N', options=end_years, index=len(end_years)-1)

laps = laps[(laps['activity_date'].dt.year >= start_year) & (laps['activity_date'].dt.year <= end_year)]

left, _, _ = st.columns(3)
with left:
    include_trail_running = st.checkbox('Inclure les sorties trail', value=False)

st.header('Temps passé dans chaque zone FC')

left, right = st.columns(2)
with left:
    ef_max = st.slider('Cardio max en EF', min_value=120, max_value=160, value=143, step=1)
with right:
    threshold = st.slider('Cardio au seuil', min_value=140, max_value=200, value=167, step=1)

if include_trail_running is False:
    laps = laps[laps['activity_type'] == 'running']

laps['time_in_ef'] = laps['moving_time'] * (laps['average_heartrate'] <= ef_max)
laps['time_in_tempo'] = laps['moving_time'] * laps['average_heartrate'].between(ef_max, threshold, inclusive='right')
laps['time_above_threshold'] = laps['moving_time'] * (laps['average_heartrate'] > threshold)

left, center, right = st.columns(3)

with left:
    st.metric('% du temps en EF', f"{laps['time_in_ef'].sum() / laps['moving_time'].sum() * 100:.1f}%")
with center:
    st.metric('% du temps en tempo', f"{laps['time_in_tempo'].sum() / laps['moving_time'].sum() * 100:.1f}%")
with right:
    st.metric('% du temps au-dessus du seuil', f"{laps['time_above_threshold'].sum() / laps['moving_time'].sum() * 100:.1f}%")
