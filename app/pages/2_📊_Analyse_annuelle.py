from datetime import datetime, date, timedelta

import streamlit as st
import plotly.express as px

from utils import db
from utils.names import NAMES

st.title('Analyse annuelle')

df = db.run_query(f"SELECT * FROM strava.activities WHERE date_part('year', start_datetime_utc) >= 2021")
df['moving_time'] = (df['moving_time'] / 3600).round(2)
df['distance'] = (df['distance'] / 1000).round(2)
df['nb_activities'] = 1
df['Type'] = df.type.map(NAMES).fillna('Autre')

metric_options = {
    "Nombre d'activités": 'nb_activities',
    "Temps d'activité": 'moving_time',
    "Distance": 'distance',
    "Distance verticale": 'total_elevation_gain',
}

years_ordered = sorted(range(2021, datetime.today().year+1, 1), reverse=True)
sports_ordered = df[df['Type'] != 'Autre'].groupby('Type')['moving_time'].sum().sort_values(ascending=False).index

st.header('Totaux par année')

left, right = st.columns(2)

with left:
    YEAR = st.selectbox('Année', options=years_ordered)
with right:
    SPORT = st.selectbox('Sport', options=['Tous les sports'] + list(sports_ordered))

df_year = df[df.start_datetime_utc.dt.year == YEAR]
df_year_prev = df[df.start_datetime_utc.dt.year == YEAR - 1]
if YEAR == date.today().year:
    df_year_prev = df_year_prev[df_year_prev.start_datetime_utc.dt.date <= date.today() - timedelta(days=365)]
if SPORT != 'Tous les sports':
    df_year = df_year[df_year["Type"] == SPORT]
    df_year_prev = df_year_prev[df_year_prev["Type"] == SPORT]

left, left_center, right_center, right = st.columns(4)

with left:
    active_days = df_year['start_datetime_utc'].dt.date.nunique()
    active_days_prev = df_year_prev['start_datetime_utc'].dt.date.nunique()
    st.metric('Jours actifs', active_days, delta=f'{(active_days / active_days_prev - 1) * 100:-.1f}%')
with left_center:
    active_time = df_year['moving_time'].sum()
    active_time_prev = df_year_prev['moving_time'].sum()
    st.metric("Temps d'activité", f"{active_time:.0f}h", delta=f'{(active_time / active_time_prev - 1) * 100:-.1f}%')
with right_center:
    total_dist = df_year['distance'].sum()
    total_dist_prev = df_year_prev['distance'].sum()
    st.metric("Total distance", f"{total_dist:.0f}km", delta=f"{(total_dist / total_dist_prev - 1) * 100:-.1f}%")
with right:
    total_dplus = df_year['total_elevation_gain'].sum()
    total_dplus_prev = df_year_prev['total_elevation_gain'].sum()
    st.metric("Total d+", f"{total_dplus:.0f}m", delta=f"{(total_dplus / total_dplus_prev - 1) * 100:-.1f}%")

st.header('Cumuls par année')

left, right, _ = st.columns(spec=(1, 1, 1))

with left:
    SPORT_CUMUL = st.selectbox('Sport', options=sports_ordered)

with right:
    metric = st.selectbox('Métrique', options=metric_options.keys(), index=2)
    metric = metric_options[metric]

df_sport = df[df["Type"] == SPORT_CUMUL]
df_sport['Année'] = df_sport['start_datetime_utc'].dt.year.astype(str)
df_sport['Semaine'] = df_sport['start_datetime_utc'].dt.isocalendar().week

df_sport_agg = df_sport.groupby(['Année', 'Semaine'])[metric].sum().reset_index(drop=False).sort_values('Semaine')
df_sport_agg['Somme cumulée'] = (df_sport_agg.groupby('Année')[metric].cumsum() * 10).round() / 10

fig = px.line(df_sport_agg, x='Semaine', y='Somme cumulée', color='Année')
fig.update_traces(hovertemplate=None)
fig.update_layout(
    hovermode="x unified",
    xaxis_title=None,
    yaxis_title=None,
)
st.plotly_chart(fig, use_container_width=True)
