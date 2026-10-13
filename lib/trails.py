import geopandas as gpd
import pandas as pd
import polyline
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import substring

from lib.database import Database


# Cut lines into pieces of about piece_length metres, keeping the index of their line and their position along it
def cut_pieces(lines: gpd.GeoSeries, piece_length: float) -> gpd.GeoDataFrame:
    pieces = []
    for index, line in lines.items():
        n = max(1, round(line.length / piece_length))
        for i in range(n):
            start, end = line.length * i / n, line.length * (i + 1) / n
            pieces.append({'line': index, 'start': start, 'end': end, 'geometry': substring(line, start, end)})
    return gpd.GeoDataFrame(pieces, geometry='geometry', crs=lines.crs)


# Pairs of piece and line where the piece runs along the line, indexed by piece, with the overlap length:
# at least min_overlap of the piece lies within tolerance of the line, and its projection on the line's stretch
# around it is at least min_span of its length, so that a line merely crossing or branching off the piece does not count
def match_pieces(pieces: gpd.GeoDataFrame, lines: gpd.GeoSeries, tolerance: float, min_overlap: float,
                 min_span: float) -> pd.DataFrame:
    buffers = lines.buffer(tolerance)
    pairs = gpd.sjoin(pieces[['geometry']], gpd.GeoDataFrame(geometry=buffers), predicate='intersects')
    overlaps, spans = [], []
    for i, j in zip(pairs.index, pairs.index_right):
        piece = pieces.geometry[i]
        stretch = lines[j].intersection(piece.buffer(tolerance))
        overlaps.append(piece.intersection(buffers[j]).length)
        # A line only touching the buffer gives a point, nothing to project on
        spans.append(abs(stretch.project(Point(piece.coords[0])) - stretch.project(Point(piece.coords[-1])))
                     if stretch.geom_type in ('LineString', 'MultiLineString') else 0)
    pairs = pd.DataFrame({'line': pairs.index_right, 'overlap': overlaps, 'span': spans}, index=pairs.index)
    length = pieces.length[pairs.index].values
    return pairs[(pairs.overlap >= min_overlap * length) & (pairs.span >= min_span * length)]


# Pieces of a zone's trails, in WGS84, with the number of activities that went along each and their first and last date
def trail_coverage(db: Database, zone: str, conf: dict) -> gpd.GeoDataFrame:
    polygon = Polygon(conf['zones'][zone])
    crs = gpd.GeoSeries([polygon], crs=4326).estimate_utm_crs()

    # Trails of the zone, cut into pieces
    trails = db.run_query(f"""
        SELECT trail_index, source, highway, balisage, etiq_num, geometry
        FROM trails.trail
        WHERE zone = '{zone}';
    """)
    trails = gpd.GeoDataFrame(trails.drop(columns='geometry'), crs=4326,
                              geometry=shapely.from_geojson(trails.geometry.values)).to_crs(crs)
    pieces = cut_pieces(trails.geometry, conf['piece_length'])

    # Tracks of the activities crossing the zone
    activities = db.run_query(f"""
        SELECT id, start_datetime_utc, polyline
        FROM strava.activities
        WHERE type IN ('{"', '".join(conf['coverage']['activity_types'])}') AND polyline <> '';
    """)
    tracks = gpd.GeoDataFrame(activities.drop(columns='polyline'), crs=4326, geometry=[
        LineString([(lon, lat) for lat, lon in polyline.decode(p)]) for p in activities.polyline
    ])
    tracks = tracks[tracks.intersects(polygon)].to_crs(crs).reset_index(drop=True)

    # Activities that went along each piece
    pairs = match_pieces(pieces, tracks.geometry, **{k: v for k, v in conf['coverage'].items() if k != 'activity_types'})
    pairs['start_datetime_utc'] = tracks.start_datetime_utc[pairs.line].values
    stats = pairs.groupby(level=0).agg(activities=('line', 'nunique'), first_datetime_utc=('start_datetime_utc', 'min'),
                                       last_datetime_utc=('start_datetime_utc', 'max'))
    pieces = pieces.join(trails.drop(columns='geometry'), on='line').join(stats)
    pieces['activities'] = pieces.activities.fillna(0).astype(int)
    pieces['length_m'] = pieces.length
    return pieces.drop(columns=['line', 'start', 'end']).to_crs(4326)
