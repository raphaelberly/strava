import datetime

import pandas as pd
import streamlit as st

from utils import db


YEAR = 2024
MONTH = datetime.date.today().month
OBJECTIVES = {
    'run': {
        'title': 'Course à pied',
        'emoji': '🏃🏼‍♂️',
        'obj': 1200,
        'obj_type': 'dist',
    },
    'ride': {
        'title': 'Vélo de route',
        'emoji': '🚴🏼‍♂️',
        'obj': 5000,
        'obj_type': 'dist',
    },
    'workout|weight': {
        'title': 'Renfo',
        'emoji': '💪🏻️',
        'obj': 40,
        'obj_type': 'count',
    },
    'backcountry': {
        'title': 'Ski de rando',
        'emoji': '⛷️',
        'obj': 5,
        'obj_type': 'count',
    },
    'alpine': {
        'title': 'Ski alpin',
        'emoji': '🚠️',
        'obj': 3,
        'obj_type': 'count',
    },
    'snowboard': {
        'title': 'Snowboard',
        'emoji': '🏂',
        'obj': 1,
        'obj_type': 'count',
    },
}

df = db.run_query(f"SELECT * FROM strava.activities")
df_year = df[df.start_datetime_utc.dt.year == YEAR]
df_month = df_year[df_year.start_datetime_utc.dt.month == MONTH]


def _display_objective(title: str, obj: str, current_total: str, current_progress: float):
    st.subheader(title)
    st.progress(
        value=min(current_progress, 1.0),
        text=f'Objectif : {obj}',
    )
    sub_left, sub_right = st.columns(2)
    with sub_left:
        st.metric('Total actuel', current_total)
    with sub_right:
        st.metric('Complétion', f'{current_progress * 100:.1f} %')


def objective(key, title, emoji, obj, obj_type):
    total_year = 0
    for k in key.split('|'):
        if obj_type == 'dist':
            total_year += df_year[df_year.type.str.lower().str.contains(k)].distance.sum() / 1000
        elif obj_type == 'count':
            total_year += len(df_year[df_year.type.str.lower().str.contains(k)])
        else:
            raise NotImplementedError('Only "dist" and "count" are supported as objective_type so far')

    _display_objective(
        title=" ".join([emoji, title]),
        obj=f'{obj} {"km" if obj_type == "dist" else "sessions"}',
        current_total=f'{total_year:.0f} {"km" if obj_type == "dist" else ""}',
        current_progress=total_year / obj,
    )


st.title(f'Objectifs {YEAR} 🎯')

st.header('Objectifs principaux')

left, right = st.columns(2, gap='medium')

with left:
    objective('run', **OBJECTIVES['run'])
with right:
    objective('ride', **OBJECTIVES['ride'])

tmp = df_year[(df_year.type.str.lower().str.contains('run') | df_year.type.str.lower().str.contains('ride'))] \
    .sort_values('start_datetime_utc', ascending=False)

st.subheader('Dernières activités')

if 'nb_activities' not in st.session_state:
    st.session_state.nb_activities = 5


def switch_df_size():
    if st.session_state.nb_activities == 20:
        st.session_state.nb_activities = 5
    else:
        st.session_state.nb_activities = 20


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
        'Vitesse (km/h)': ((tmp.distance / 1000) / (tmp.moving_time / 3600)).round(1),
        'url': 'https://www.strava.com/activities/' + tmp.id.astype(str),
    }).head(st.session_state.nb_activities),
    hide_index=True,
    use_container_width=True,
    column_config={'url': st.column_config.LinkColumn("URL Strava")},
)
st.button(label=f'Voir {"plus" if st.session_state.nb_activities == 5 else "moins"}', on_click=switch_df_size())


st.header('Objectifs secondaires')

left, right = st.columns(2, gap='medium')

with left:
    sport = 'workout|weight'
    objective(sport, **OBJECTIVES[sport])
    sport = 'alpine'
    objective(sport, **OBJECTIVES[sport])
with right:
    sport = 'backcountry'
    objective(sport, **OBJECTIVES[sport])
    sport = 'snowboard'
    objective(sport, **OBJECTIVES[sport])
