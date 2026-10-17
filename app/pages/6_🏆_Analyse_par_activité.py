import plotly.express as px
import streamlit as st

from autenthicator import authenticate
from utils.loader import fetch_laps_df

# Make sure the user is logged in
authenticate()

# Lap metrics that can be plotted, with their label
METRICS = {
    'speed_to_heartrate': 'Vitesse / FC',
    'power_to_heartrate': 'Puissance / FC',
    'stride_length': 'Longueur de foulée',
    'average_speed': 'Vitesse moyenne',
    'average_cadence': 'Cadence moyenne',
    'average_heartrate': 'FC moyenne',
    'vertical_oscillation': 'Oscillation verticale',
    'vertical_ratio': 'Rapport vertical',
    'ground_contact_balance': 'Équilibre du temps de contact au sol',
    'ground_contact_time': 'Temps de contact au sol',
}


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

laps = fetch_laps_df()
laps.rename(columns={'activity_start_datetime_utc': 'activity_date'}, inplace=True)
laps = laps[laps['moving_time'] >= 20]
laps['max_pace'] = laps['max_speed'].apply(calculate_pace)
laps['average_pace'] = laps['average_speed'].apply(calculate_pace)
laps['power_to_heartrate'] = laps['average_power'].divide(laps['average_heartrate'])
laps['speed_to_heartrate'] = laps['average_speed'].divide(laps['average_heartrate'])

activities = laps.sort_values('activity_date', ascending=False)[['activity_id', 'activity_name']].drop_duplicates()
# Some Garmin activities have no name, which pandas reads as NaN
activities['activity_name'] = activities['activity_name'].fillna('Sans nom')

names = dict(zip(activities.activity_id, activities.activity_name))
activity_id = st.selectbox('Activité', options=activities.activity_id, format_func=names.get)

df = laps[laps.activity_id == activity_id]

left, center, _ = st.columns(3)

with left:
    y = st.selectbox('Y', options=list(METRICS), format_func=METRICS.get)

exclude_slow_laps = st.checkbox('Enlever les circuits lents', value=True)

if exclude_slow_laps:
    df = df[df['average_pace'] < 6*60]

# Create plotly figure with a scatterplot with power_to_hr as a function of lap_index, Add a trendline, and Do not show any legend
fig = px.scatter(df, x='lap_index', y=y, trendline='ols')

fig.update_traces(marker=dict(size=10))
fig.update_layout(
    xaxis_title='Circuit',
    yaxis_title=METRICS[y],
)
st.plotly_chart(fig)
