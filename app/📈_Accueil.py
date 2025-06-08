import pandas as pd
import streamlit as st

from utils import db
from utils.navigation import switch_page

# First streamlit command
st.set_page_config(
    page_title="Health & Sports",
    page_icon="📈",
)

st.title(f'Bienvenue ! 👋🏻')

st.subheader('Choisir un outil')

if st.button('🎯 Objectifs'):
    switch_page('objectifs')

if st.button('📊 Analyse annuelle'):
    switch_page('analyse annuelle')

if st.button('🏃🏼‍♂️ Analyse de foulée'):
    switch_page('analyse de foulée')

if st.button('🧘🏼 Analyse de volume'):
    switch_page('analyse du volume')


st.subheader('Dernières activités')

if 'nb_activities' not in st.session_state:
    st.session_state.nb_activities = 5


def switch_df_size():
    if st.session_state.nb_activities == 30:
        st.session_state.nb_activities = 5
    else:
        st.session_state.nb_activities = 30


df = db.run_query(f"SELECT * FROM strava.activities")
tmp = df[(df.type.str.lower().str.contains('run') | df.type.str.lower().str.contains('ride'))] \
    .sort_values('start_datetime_utc', ascending=False)

st.dataframe(
    data=pd.DataFrame({
        'Date': tmp.start_datetime_utc.dt.date,
        'Type': tmp.type.map({
            'Run': '🏃🏼‍♂️',
            'Ride': '🚴🏼‍♂️',
            'VirtualRide': '🚴🏼‍♂️',
        }),
        'Nom': tmp.name,
        'Distance (km)': (tmp.distance / 1000).round(2),
        'D+ (m)': tmp.total_elevation_gain.round(),
        'url': 'https://www.strava.com/activities/' + tmp.id.astype(str),
    }).head(st.session_state.nb_activities),
    hide_index=True,
    use_container_width=True,
    column_config={'url': st.column_config.LinkColumn("URL Strava")},
)
st.button(label=f'Voir {"plus" if st.session_state.nb_activities == 5 else "moins"}', on_click=switch_df_size())


st.subheader('Rafraîchir')

if st.button('Rafraîchir les sources de données'):
    st.cache_data.clear()
    st.rerun()
