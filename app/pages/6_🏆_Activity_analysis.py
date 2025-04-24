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
laps['power_to_heartrate'] = laps['average_power'].divide(laps['average_heartrate'])
laps['speed_to_heartrate'] = laps['average_speed'].divide(laps['average_heartrate'])

activities = laps.sort_values('activity_date', ascending=False)[['activity_id', 'activity_name']].drop_duplicates()

activity_id = st.selectbox('Activity', options=activities.activity_id, format_func=lambda n: dict(zip(activities.activity_id, activities.activity_name))[n])

df = laps[laps.activity_id == activity_id]

left, center, _ = st.columns(3)

with left:
    y = st.selectbox('Y', options=[
        'speed_to_heartrate',
        'power_to_heartrate',
        'stride_length',
        'average_speed',
        'average_cadence',
        'average_heartrate',
        'vertical_oscillation',
        'vertical_ratio',
        'ground_contact_balance',
        'ground_contact_time',
    ], format_func=normalize_text)

exclude_slow_laps = st.checkbox('Exclude slow laps', value=True)

if exclude_slow_laps:
    df = df[df['average_pace'] < 6*60]

# Create plotly figure with a scatterplot with power_to_hr as a function of lap_index, Add a trendline, and Do not show any legend
import plotly.express as px
fig = px.scatter(df, x='lap_index', y=y, trendline='ols')

fig.update_traces(marker=dict(size=10))
fig.update_layout(
    xaxis_title='Lap index',
    yaxis_title=y.capitalize(),
)
st.plotly_chart(fig, use_container_width=True)
