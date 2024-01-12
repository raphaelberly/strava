import datetime

import pandas as pd
import streamlit as st
from yaml import safe_load

from utils import db


YEAR = 2024
MONTH = datetime.date.today().month
DOY = datetime.datetime.now().timetuple().tm_yday
OBJECTIVES = safe_load(open('conf/objectives.yaml'))

df = db.run_query(f"SELECT * FROM strava.activities")
df_year = df[df.start_datetime_utc.dt.year == YEAR]
df_month = df_year[df_year.start_datetime_utc.dt.month == MONTH]


def _display_objective(title: str, obj: str, current_total: str, current_progress: float, delta: str = None):
    st.subheader(title)
    st.progress(
        value=min(current_progress, 1.0),
        text=f'Objectif : {obj}',
    )
    sub_left, sub_right = st.columns(2)
    with sub_left:
        if delta:
            delta_color = 'inverse' if 'behind' in delta else 'normal'
            st.metric('Total actuel', current_total, delta=delta, delta_color=delta_color)
        else:
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

    _delta = (total_year / obj - DOY / 365) * obj if obj_type == 'dist' else None
    _display_objective(
        title=" ".join([emoji, title]),
        obj=f'{obj} {"km" if obj_type == "dist" else "sessions"}',
        current_total=f'{total_year:.0f} {"km" if obj_type == "dist" else ""}',
        current_progress=total_year / obj,
        delta=f"{abs(_delta):.0f} km {'behind' if _delta < 0 else 'ahead'}" if _delta else None,
    )


st.title(f'Objectifs {YEAR} 🎯')

st.header('Objectifs principaux')

left, right = st.columns(2, gap='medium')

with left:
    objective('run', **OBJECTIVES['run'])
with right:
    objective('ride', **OBJECTIVES['ride'])

st.subheader('Dernières activités')

if 'nb_activities' not in st.session_state:
    st.session_state.nb_activities = 5


def switch_df_size():
    if st.session_state.nb_activities == 20:
        st.session_state.nb_activities = 5
    else:
        st.session_state.nb_activities = 20


tmp = df_year[(df_year.type.str.lower().str.contains('run') | df_year.type.str.lower().str.contains('ride'))] \
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
