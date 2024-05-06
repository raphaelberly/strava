import re

import numpy as np
import plotly.express as px
import streamlit as st

from utils import db


st.title('🚴🏼‍♂️ Zwift analysis')

df = db.run_query(f"SELECT * FROM strava.activities_curated WHERE ftp_base_w IS NOT NULL")


def parse_name(name: str) -> str:
    search = re.search(r'^zwift #(\d+) - (.+)$', name, re.IGNORECASE)
    if search:
        return search.group(2)


df['exercise_name'] = df.name.apply(parse_name)
df = df.loc[~df['exercise_name'].isnull()]

df['exercise_count'] = df.groupby('exercise_name').exercise_name.transform('count')

filter_out_single = st.checkbox('Show only exercises done 2+ times', value=True)
df = df[df['exercise_count'] > int(filter_out_single)]

exercises_sorted = df.sort_values('exercise_count', ascending=False).exercise_name.unique()
exercise = st.selectbox('Pick exercise', options=exercises_sorted)

df = df.loc[df['exercise_name'] == exercise]


df['Base de FTP (w)'] = df.ftp_base_w.apply(lambda x: f'{x}w')
df["Mesure d'effort"] = df.relative_effort
df['Puissance (w)'] = df.average_power_w.round().astype(int)
df['Date'] = df.start_date

st.dataframe(
    data=df[['Date', 'Base de FTP (w)', "Mesure d'effort", 'Puissance (w)']].set_index('Date').sort_index(),
    use_container_width=True,
)

fig = px.scatter(df, x='Date', y="Mesure d'effort",
                 color='Base de FTP (w)',
                 category_orders={'Base de FTP (w)': np.sort(df['Base de FTP (w)'].unique())},
                 color_discrete_sequence=px.colors.sequential.Reds,
                 )
fig.update_traces(marker=dict(size=12))

# Displaying the plot
st.plotly_chart(figure_or_data=fig)
