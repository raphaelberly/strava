import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml
from shapely.geometry import Polygon

from autenthicator import authenticate
from utils import db
from lib.trails import trail_coverage

# Make sure the user is logged in
authenticate()

CONF = yaml.safe_load(open('../conf/trails.yaml'))
MAPBOX_TOKEN = yaml.safe_load(open('../conf/secrets.yaml'))['mapbox']['token']
# Legend, colour and width of the map's lines, by (covered, marked)
STYLES = {
    (True, True): ('Sentiers balisés parcourus', '#2b8a3e', 4),
    (True, False): ('Autres sentiers parcourus', '#2b8a3e', 2),
    (False, True): ('Sentiers balisés vierges', '#e03131', 4),
    (False, False): ('Autres sentiers vierges', '#f08c00', 2),
}


# Coverage takes a few seconds to compute: keep it for an hour, activities come in hourly
@st.cache_data(ttl=3600)
def load_coverage(zone):
    return trail_coverage(db, zone, CONF)


# Hover text of a piece of trail
def label(piece):
    if pd.notna(piece.balisage):
        number = piece.etiq_num if pd.notna(piece.etiq_num) else ''
        trail = f'Sentier {piece.balisage.replace(";", " + ")} {number}'.strip()
    else:
        trail = 'Sentier non balisé'
    if piece.activities == 0:
        return f'{trail}<br>Jamais parcouru'
    return f'{trail}<br>{piece.activities} passage{"s" if piece.activities > 1 else ""}, ' \
           f'le dernier le {piece.last_datetime_utc:%d/%m/%Y}'


st.title('🥾 Sentiers')

zones = list(CONF['zones'])
zone = st.selectbox('Massif', zones, format_func=str.capitalize) if len(zones) > 1 else zones[0]
pieces = load_coverage(zone)
covered = pieces.activities > 0
marked = pieces.balisage.notna()

# Completion, of all trails and of the trails marked by the park
for column, title, subset in zip(st.columns(2), ['Tous les sentiers', 'Sentiers balisés'], [pieces, pieces[marked]]):
    with column:
        done_km = subset.length_m[subset.activities > 0].sum() / 1000
        total_km = subset.length_m.sum() / 1000
        st.metric(title, f'{done_km / total_km:.0%}')
        st.progress(done_km / total_km, text=f'{done_km:.1f} km parcourus sur {total_km:.1f} km')

# Map, one trace per style, each piece of trail drawn as its own line
fig = go.Figure()
for (is_covered, is_marked), (name, colour, width) in STYLES.items():
    lon, lat, text = [], [], []
    for piece in pieces[(covered == is_covered) & (marked == is_marked)].itertuples():
        xs, ys = piece.geometry.xy
        lon += [*xs, None]
        lat += [*ys, None]
        text += [label(piece)] * len(xs) + [None]
    fig.add_trace(go.Scattermap(lon=lon, lat=lat, mode='lines', name=name, line={'color': colour, 'width': width},
                                hovertext=text, hoverinfo='text'))
center = Polygon(CONF['zones'][zone]).centroid
fig.update_layout(
    map={
        'style': 'white-bg',
        'center': {'lon': center.x, 'lat': center.y},
        'zoom': 13,
        # Mapbox Outdoors as raster tiles: plotly's maps are MapLibre, which cannot load Mapbox styles themselves
        'layers': [{
            'sourcetype': 'raster',
            'source': [f'https://api.mapbox.com/styles/v1/mapbox/outdoors-v12/tiles/256/{{z}}/{{x}}/{{y}}@2x'
                       f'?access_token={MAPBOX_TOKEN}'],
            'sourceattribution': '© Mapbox, © OpenStreetMap',
            'below': 'traces',
        }],
    },
    height=700,
    margin={'l': 0, 'r': 0, 't': 0, 'b': 0},
    # Dark text on a light box, over the map whatever the app's theme
    legend={'x': 0.01, 'y': 0.99, 'bgcolor': 'rgba(255, 255, 255, 0.8)', 'font': {'color': '#212529'}},
)
st.plotly_chart(fig)
