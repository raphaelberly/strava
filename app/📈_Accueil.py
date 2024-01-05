import streamlit as st

from utils.navigation import switch_page

# from autenthicator import authenticate

# First streamlit command
st.set_page_config(
    page_title="Health & Sports",
    page_icon="📈",
)
# Make sure the user is logged in
# username = authenticate()

# st.title(f'Bienvenue, {username}! 👋🏻')
st.title(f'Bienvenue ! 👋🏻')

st.subheader('Choisir un outil')

if st.button('🎯 Objectifs'):
    switch_page('objectifs')

if st.button('📊 Analyse annuelle'):
    switch_page('analyse annuelle')

st.subheader('Rafraîchir')

if st.button('Rafraîchir les sources de données'):
    st.cache_data.clear()
    st.rerun()
