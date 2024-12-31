import streamlit as st

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

st.subheader('Rafraîchir')

if st.button('Rafraîchir les sources de données'):
    st.cache_data.clear()
    st.rerun()
