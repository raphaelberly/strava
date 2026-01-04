import datetime

import streamlit as st
from yaml import safe_load

from utils import db

YEAR = 2026
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
    sub_left, sub_right = st.columns(spec=[3,2])
    with sub_left:
        if delta:
            delta_color = 'inverse' if 'de retard' in delta else 'normal'
            st.metric('Total actuel', current_total, delta=delta, delta_color=delta_color)
        else:
            st.metric('Total actuel', current_total)
    with sub_right:
        st.metric('Complétion', f'{current_progress * 100:.1f} %')


def objective(title, emoji, sports, obj, obj_type, filter_string='', filter_dist=0):
    UNITS = {
        'dist': 'km',
        'count': 'sessions',
        'elev': 'm',
    }
    total_year = 0
    df = df_year[df_year.name.str.lower().str.contains(filter_string.lower())].copy()
    df = df[df.distance / 1000 >= filter_dist]
    for sport in sports:
        if obj_type == 'dist':
            total_year += df[df.type.str.lower().str.contains(sport)].distance.sum() / 1000
        elif obj_type == 'count':
            total_year += len(df[df.type.str.lower().str.contains(sport)])
        elif obj_type == 'elev':
            total_year += df[df.type.str.lower().str.contains(sport)].total_elevation_gain.sum()
        else:
            raise NotImplementedError(f'Only {UNITS.keys()} are supported as objective_type so far')

    _delta = float((total_year / obj - DOY / 365) * obj).__round__(0)
    if _delta == 0:
        delta_str = "Pile sur l'objectif"
    else:
        delta_str = f"""{abs(_delta):.0f} {UNITS[obj_type]} {'de retard' if _delta < 0 else "d'avance"}"""
    _display_objective(
        title=" ".join([emoji, title]),
        obj=f'{obj} {UNITS[obj_type]}',
        current_total=f'{total_year:.0f} {UNITS[obj_type]}',
        current_progress=total_year / obj,
        delta=delta_str,
    )


st.title(f'Objectifs {YEAR} 🎯')

st.header('Objectifs principaux')

left, right = st.columns(2, gap='medium')

with left:
    objective(**OBJECTIVES['run'])
    objective(**OBJECTIVES['hiit'])
with right:
    objective(**OBJECTIVES['ride'])
    objective(**OBJECTIVES['feet_elev'])

st.header('Objectifs secondaires')

left, right = st.columns(2, gap='medium')

with left:
    objective(**OBJECTIVES['run_20ks'])
with right:
    objective(**OBJECTIVES['run_30ks'])
