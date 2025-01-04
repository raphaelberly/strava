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

st.title('Analyse de foulée 🏃🏼‍♂️')

left, center, right = st.columns(3)

with left:
    include_trail_running = st.checkbox('Inclure les sorties trail', value=False)
with center:
    filter_out_slow_laps = st.checkbox('Enlever les circuits lents', value=True)

if include_trail_running is False:
    laps = laps[laps['activity_type'] == 'running']
if filter_out_slow_laps:
    laps = laps[laps['average_pace'] <= 7*60]

years = sorted(list(set(laps['activity_date'].dt.year)))
with left:
    start_year = st.selectbox(label='Année 1', options=years, index=0)
with center:
    end_years = [y for y in years if y >= start_year]
    end_year = st.selectbox(label='Année N', options=end_years, index=len(end_years)-1)

laps = laps[(laps['activity_date'].dt.year >= start_year) & (laps['activity_date'].dt.year <= end_year)]

left, center, right = st.columns(3)

with left:
    x = st.selectbox('X', options=[
        'average_pace',
        'average_cadence',
        'average_heartrate',
        'activity_date',
        'max_pace',
        'max_heartrate',
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
with right:
    c = st.selectbox('Color', options=[
        '',
        'average_pace',
        'average_cadence',
        'average_heartrate',
    ], format_func=normalize_text)

# Format the ticks on the x-axis
trace_marker = {'size': 10, 'opacity': 0.7}
if c != '':
    trace_marker.update({
        'color': laps[c].tolist(),
        'colorscale': 'Blues',  # https://media.geeksforgeeks.org/wp-content/uploads/20220220154706/newplot.png
    })
trace = go.Scatter(
    x=laps[x],
    y=laps[y].round(2),
    mode='markers',
    marker=trace_marker,
    hovertemplate=f'{normalize_text(y)} : <b>%{{y}}</b>'
                  f'<br>Date : %{{customdata[0]}}'
                  f'<br>Nom : %{{customdata[1]}}'
                  f'<br>Circuit : %{{customdata[2]}}'
                  f'<br>Allure : %{{customdata[3]}}'
                  f'<br>Durée : %{{customdata[4]}}',
    customdata=list(zip(
        laps['activity_date'].dt.strftime('%b %d, %Y').tolist(),
        laps['activity_name'].tolist(),
        laps['lap_index'].tolist(),
        laps['average_pace'].apply(format_pace).tolist(),
        laps['moving_time'].apply(format_duration).tolist(),
    )),
)

layout=None
if 'pace' in x:
    num_ticks = 12
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
