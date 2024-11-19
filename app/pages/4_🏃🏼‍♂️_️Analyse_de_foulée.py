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

laps = db.run_query('SELECT * FROM garmin.lap_enriched')


st.title('Analyse de foulée 🏃🏼‍♂️')

sports_list = [item for item in laps['activity_type'].unique()]
sports = st.selectbox('Sport', ['Toutes les sorties course à pied'] + sports_list, format_func=normalize_text, index=1)
if sports != 'Toutes les sorties course à pied':
    laps = laps[laps['activity_type'] == sports]

years = sorted(list(set(laps['activity_start_datetime_utc'].dt.year)))
left, center, _ = st.columns(3)
with left:
    start_year = st.selectbox(label='Année 1', options=years, index=0)
with center:
    end_years = [y for y in years if y >= start_year]
    end_year = st.selectbox(label='Année N', options=end_years, index=len(end_years)-1)

laps = laps[(laps['activity_start_datetime_utc'].dt.year >= start_year) & laps['activity_start_datetime_utc'].dt.year <= end_year]

laps['max_pace'] = laps['max_speed'].apply(calculate_pace)
laps['average_pace'] = laps['average_speed'].apply(calculate_pace)

with left:
    x = st.selectbox('X', options=[
        'max_pace',
        'average_pace',
        'average_cadence',
        'average_heartrate',
        'max_heartrate',
        'activity_start_datetime_utc',
    ], format_func=normalize_text)
with center:
    y = st.selectbox('Y', options=[
        'stride_length',
        'average_cadence',
        'vertical_oscillation',
        'vertical_ratio',
        'ground_contact_balance',
        'ground_contact_time',
    ], format_func=normalize_text)

# Format the ticks on the x-axis
trace = go.Scatter(
    x=laps[x],
    y=laps[y].round(2),
    mode='markers',
    hovertemplate=normalize_text(y) + ': <b>%{y}</b><br>Name: %{customdata[0]}<br>Lap: %{customdata[1]}<br>Pace: %{customdata[2]}',
    customdata=list(zip(
        laps['activity_name'].tolist(),
        laps['lap_index'].tolist(),
        laps['average_pace'].apply(format_pace).tolist(),
    ))
)

layout=None
if 'pace' in x:
    num_ticks = 6
    min_pace = round(laps[x].min() / 60) * 60
    max_pace = round(laps[x].max() / 60 + 1) * 60
    tickvals = np.linspace(min_pace, max_pace, num_ticks)
    layout = go.Layout(
        xaxis=dict(
            tickvals=tickvals,
            ticktext=[format_pace(pace) for pace in tickvals],
        )
    )

fig = go.Figure(data=[trace], layout=layout)
st.plotly_chart(fig, use_container_width=True)
