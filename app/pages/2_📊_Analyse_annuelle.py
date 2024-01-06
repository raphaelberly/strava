from datetime import date, timedelta

import streamlit as st
import plotly.express as px

from utils import db
from utils.names import NAMES

st.title('Analyse annuelle')

st.header('Statistiques')

YEAR = st.selectbox('Année', options=[2024, 2023, 2022, 2021])

df = db.run_query(f"SELECT * FROM strava.activities WHERE date_part('year', start_datetime_utc) >= 2021")
df['moving_time'] = (df['moving_time'] / 3600).round(2)
df['distance'] = (df['distance'] / 1000).round(2)
df['nb_activities'] = 1
df['Type'] = df.type.map(NAMES).fillna('Autre')


df_year = df[df.start_datetime_utc.dt.year == YEAR]
df_year_prev = df[df.start_datetime_utc.dt.year == YEAR - 1]
if YEAR == date.today().year:
    df_year_prev = df_year_prev[df_year_prev.start_datetime_utc.dt.date <= date.today() - timedelta(days=365)]

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


st.subheader('Répartition par sport')

metric_options = {
    "Nombre d'activités": 'nb_activities',
    "Temps d'activité": 'moving_time',
    "Distance": 'distance',
    "Distance verticale": 'total_elevation_gain',
}

left, right = st.columns(spec=(1, 2))

with left:
    base = st.selectbox('Base', options=metric_options.keys(), index=1)
    base = metric_options[base]

with right:

    fig1 = px.pie(
        data_frame=df_year,
        values=base,
        names='Type',
        hole=0.5,
        height=350,
    )
    fig1.update_layout(
        showlegend=False,
        margin=dict(l=0, t=0, r=0, b=120),
    )
    fig1.update_traces(
        hovertemplate=None,
        textinfo='label+percent'
    )
    st.plotly_chart(fig1, theme="streamlit", use_container_width=True)

st.header('Totaux cumulés par année')

left, right, _ = st.columns(spec=(1, 1, 1))

with left:
    sports_ordered = df_year[df_year['Type'] != 'Autre'].groupby('Type')['moving_time'].sum()\
        .sort_values(ascending=False).index
    sport = st.selectbox('Sport', options=sports_ordered)

with right:
    metric = st.selectbox('Métrique', options=metric_options.keys(), index=2)
    metric = metric_options[metric]

df_sport = df[df["Type"] == sport]
df_sport['Année'] = df_sport['start_datetime_utc'].dt.year.astype(str)
df_sport['Semaine'] = df_sport['start_datetime_utc'].dt.isocalendar().week

df_sport_agg = df_sport.groupby(['Année', 'Semaine'])[metric].sum().reset_index(drop=False).sort_values('Semaine')
df_sport_agg['Somme cumulée'] = df_sport_agg.groupby('Année')[metric].cumsum()

st.line_chart(df_sport_agg, x='Semaine', y='Somme cumulée', color='Année')
