from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import db
from utils.names import NAMES

st.title('Analyse globale')

df = db.run_query(f"SELECT * FROM strava.activities WHERE date_part('year', start_datetime_utc) >= 2021")
df['moving_time'] = (df['moving_time'] / 3600).round(2)
df['distance'] = (df['distance'] / 1000).round(2)
df['nb_activities'] = 1
df['Type'] = df.type.map(NAMES).fillna('Autre')
# For "Renfo" we filter out on the activity name
df.loc[(df['Type'] == 'Renfo') &
       (~df.name.str.lower().str.contains('hiit') & ~df.name.str.lower().str.contains('renfo')), 'Type'] = 'Autre'
df['nb_longer_than_20k'] = (df['distance'] >= 20).astype(int)
df['nb_interval_trainings'] = df['name'].str.lower().str.contains('frac').astype(int)

sports_ordered = df[df['Type'] != 'Autre'].groupby('Type')['moving_time'].sum().sort_values(ascending=False).index

SPORTS = st.multiselect(label='Sports', options=sports_ordered) or list(sports_ordered)

metric_options = {
    "Nombre d'activités": 'nb_activities',
    "Temps d'activité": 'moving_time',
    "Distance": 'distance',
    "Distance verticale": 'total_elevation_gain',
    "Nombre de fractionnés": 'nb_interval_trainings',
    "Nombre de sorties de 20k+": 'nb_longer_than_20k',
}

left, _ = st.columns(2)
with left:
    metric_name = st.selectbox('Métrique', options=metric_options.keys(), index=2)
    METRIC = metric_options[metric_name]

df_sport = df[df["Type"].isin(SPORTS)]
df_sport['Année'] = df_sport['start_datetime_utc'].dt.year.astype(str)

df_sport_agg = df_sport.groupby(['Année'])[METRIC].sum().reset_index(drop=False).sort_values('Année')

# Calculate projected value for current year
current_year = str(datetime.now().year)
current_day_of_year = datetime.now().timetuple().tm_yday

df_sport_agg['projected_value'] = df_sport_agg[METRIC]
if current_year in df_sport_agg['Année'].values:
    current_value = df_sport_agg.loc[df_sport_agg['Année'] == current_year, METRIC].values[0]
    projected_value = current_value * (365 / current_day_of_year)
    df_sport_agg.loc[df_sport_agg['Année'] == current_year, 'projected_value'] = projected_value

# Calculate year-over-year percentage change using projected value for current year
df_sport_agg['pct_change'] = df_sport_agg['projected_value'].pct_change() * 100

# Create text labels for percentage change (e.g., "+14%")
df_sport_agg['label'] = df_sport_agg['pct_change'].apply(
    lambda x: f"{'+' if x >= 0 else ''}{x:.1f}%" if pd.notna(x) and np.isfinite(x) else ""
)
df_sport_agg['label_color'] = df_sport_agg['pct_change'].apply(lambda x: '#2ecc71' if x >= 0 else '#e74c3c')

# Create bar chart with graph_objects for more control
fig = go.Figure()

# Add projected bar for current year first (so it appears in background with overlay mode)
if current_year in df_sport_agg['Année'].values:
    current_row = df_sport_agg[df_sport_agg['Année'] == current_year].iloc[0]
    projected_value = current_row['projected_value']
    pct_change = current_row['pct_change']

    # Format percentage change with color indicator
    if pd.notna(pct_change) and np.isfinite(pct_change):
        pct_text = f"{'+' if pct_change > 0 else ''}{pct_change:.1f}%"
    else:
        pct_text = ""

    fig.add_trace(go.Bar(
        x=[current_year],
        y=[projected_value],
        marker_color='rgba(52, 152, 219, 0.3)',  # Translucent blue
        showlegend=False,
        customdata=[[pct_text]],
        hovertemplate=f'<b>%{{y:.2f}}</b> (%{{customdata[0]}})<br><extra></extra>'
    ))

# Prepare customdata for actual bars (percentage change for each year)
customdata_actual = []
for idx, row in df_sport_agg.iterrows():
    if row['label']:
        # For other years with labels, show the percentage
        customdata_actual.append([f" ({row['label']})"])
    else:
        customdata_actual.append([''])

# Add actual values bars on top
fig.add_trace(go.Bar(
    x=df_sport_agg['Année'],
    y=df_sport_agg[METRIC],
    marker_color='#3498db',
    customdata=customdata_actual,
    hovertemplate=f'<b>%{{y:.2f}}</b> %{{customdata[0]}}<br><extra></extra>'
))

fig.update_layout(
    showlegend=False,
    barmode='overlay',  # Overlay bars so projected bar appears behind
    margin=dict(t=20, b=40, l=40, r=20)  # Reduce top margin to minimize empty space
)

# Add colored text annotations for percentage change
for idx, row in df_sport_agg.iterrows():
    if row['label']:
        # For current year, place label on projected bar; for others, on actual bar
        y_position = row['projected_value'] if row['Année'] == current_year else row[METRIC]
        fig.add_annotation(
            x=row['Année'],
            y=y_position,
            text=row['label'],
            showarrow=False,
            yshift=10,
            font=dict(size=12, color=row['label_color'])
        )

# Display the chart
st.plotly_chart(fig, use_container_width=True)
