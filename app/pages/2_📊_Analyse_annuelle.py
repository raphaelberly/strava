from cProfile import label
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
df['nb_longer_than_20k'] = (df['distance'] >= 20).astype(int)
df['nb_interval_trainings'] = df['name'].str.lower().str.contains('frac').astype(int)

years_ordered = sorted(range(2021, datetime.today().year+1, 1), reverse=True)
sports_ordered = df[df['Type'] != 'Autre'].groupby('Type')['moving_time'].sum().sort_values(ascending=False).index

SPORTS = st.multiselect(label='Sports', options=sports_ordered) or list(sports_ordered)

st.header('Bilan par année')

left, _, _ = st.columns(3)
with left:
    YEAR = st.selectbox('Année', options=years_ordered)

df_year = df[df.start_datetime_utc.dt.year == YEAR]
df_year_prev = df[df.start_datetime_utc.dt.year == YEAR - 1]
if YEAR == date.today().year:
    df_year_prev = df_year_prev[df_year_prev.start_datetime_utc.dt.date <= date.today() - timedelta(days=365)]
df_year = df_year[df_year["Type"].isin(SPORTS)]
df_year_prev = df_year_prev[df_year_prev["Type"].isin(SPORTS)]

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

st.header('Totaux cumulés')

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
    metric = st.selectbox('Métrique', options=metric_options.keys(), index=2)
    metric = metric_options[metric]

df_sport = df[df["Type"].isin(SPORTS)]
df_sport['Année'] = df_sport['start_datetime_utc'].dt.year.astype(str)
df_sport['Semaine'] = df_sport['start_datetime_utc'].dt.isocalendar().week

df_sport_agg = df_sport.groupby(['Année', 'Semaine'])[metric].sum().reset_index(drop=False).sort_values('Semaine')
df_sport_agg['Somme cumulée'] = (df_sport_agg.groupby('Année')[metric].cumsum() * 10).round() / 10

fig = px.line(df_sport_agg, x='Semaine', y='Somme cumulée', color='Année')
fig.update_traces(hovertemplate=None)
fig.for_each_trace(lambda t: t.update(name=t.name))  # Make the captions ordered
fig.update_layout(
    hovermode="x unified",
    xaxis_title=None,
    yaxis_title=None,
)
st.plotly_chart(fig, use_container_width=True)
