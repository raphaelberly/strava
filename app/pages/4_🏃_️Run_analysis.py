import streamlit as st
import numpy as np
from utils import db
import altair as alt


def normalize_text(text: str):
    return ' '.join(text.split('_')).capitalize()


activities = db.run_query('SELECT * FROM garmin.activity_enriched')
laps = db.run_query('SELECT * FROM garmin.lap_enriched')


st.title('Analyse de course à pied')

sports_list = [item for item in activities['type'].unique()]
sports = st.selectbox('Sport', ['Toutes les sorties course à pied'] + sports_list, format_func=normalize_text)
if sports != 'Toutes les sorties course à pied':
    activities = activities[activities['type'] == sports]
    laps = laps[laps['activity_type'] == sports]

years = sorted(list(set(activities['start_datetime_utc'].dt.year)))
left, center, _ = st.columns(3)
with left:
    start_year = st.selectbox(label='Année 1', options=years, index=0)
with center:
    end_years = [y for y in years if y >= start_year]
    end_year = st.selectbox(label='Année N', options=end_years, index=len(end_years)-1)

activities = activities[(activities['start_datetime_utc'].dt.year >= start_year) & activities['start_datetime_utc'].dt.year <= end_year]
laps = laps[(laps['activity_start_datetime_utc'].dt.year >= start_year) & laps['activity_start_datetime_utc'].dt.year <= end_year]

activities['Semaine'] = activities['start_datetime_utc'].dt.date - activities['start_datetime_utc'].dt.weekday * np.timedelta64(1, 'D')
activities['Balance G/D'] = activities['ground_contact_balance'] - 50

lr_balance = activities.groupby('Semaine').agg({'Balance G/D': lambda x: np.average(x, weights=activities.loc[x.index, 'distance'], axis=0)})

st.scatter_chart(lr_balance)

st.header('Stride exploration')

min_speed = st.slider('Min speed', min_value=laps.average_speed.min(), max_value=laps.average_speed.max())

laps = laps[laps.average_speed >= min_speed]

x = st.selectbox('X', options=[
    'average_speed',
    'max_speed',
    'max_vertical_speed',
    'average_cadence',
    'average_heartrate',
    'max_heartrate',
    'activity_start_datetime_utc',
], format_func=normalize_text)
y = st.selectbox('Y', options=[
    'stride_length',
    'average_cadence',
    'vertical_oscillation',
    'vertical_ratio',
    'ground_contact_balance',
    'ground_contact_time',
], format_func=normalize_text)

c = (
   alt.Chart(laps)
   .mark_circle()
   .encode(x=alt.X(x).scale(zero=False), y=alt.Y(y).scale(zero=False), color=y, tooltip=['activity_name', 'lap_index', 'activity_start_datetime_utc', 'moving_time'])
)

st.altair_chart(c, use_container_width=True)
