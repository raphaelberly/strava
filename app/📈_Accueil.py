import pandas as pd
import streamlit as st

from autenthicator import authenticate
from utils import db

# First streamlit command
st.set_page_config(
    page_title="Strava",
    page_icon="📈",
)
# Make sure the user is logged in
authenticate()

st.title(f'Bienvenue ! 👋🏻')

st.subheader('Choisir un outil')

if st.button('🎯 Objectifs'):
    st.switch_page('pages/1_🎯_Objectifs.py')

if st.button('📈 Analyse annuelle'):
    st.switch_page('pages/2_📈_Analyse_annuelle.py')

if st.button('📊 Analyse globale'):
    st.switch_page('pages/2_📊_Analyse_globale.py')

if st.button('🏃🏼‍♂️ Analyse de foulée'):
    st.switch_page('pages/4_🏃🏼‍♂️_Analyse_de_foulée.py')

if st.button('🧘🏼 Analyse de volume'):
    st.switch_page('pages/5_🧘🏼_Analyse_du_volume.py')


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
            'TrailRun': '🏃🏼‍♂️',
            'Ride': '🚴🏼‍♂️',
            'VirtualRide': '🚴🏼‍♂️',
        }),
        'Nom': tmp.name,
        'Distance (km)': (tmp.distance / 1000).round(2),
        'D+ (m)': tmp.total_elevation_gain.round(),
        'url': 'https://www.strava.com/activities/' + tmp.id.astype(str),
    }).head(st.session_state.nb_activities),
    hide_index=True,
    column_config={'url': st.column_config.LinkColumn("URL Strava")},
)
st.button(label=f'Voir {"plus" if st.session_state.nb_activities == 5 else "moins"}', on_click=switch_df_size)


st.subheader('Rafraîchir')

if st.button('Rafraîchir les sources de données'):
    st.cache_data.clear()
    st.rerun()
