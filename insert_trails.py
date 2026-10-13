import argparse
import io
import json
import logging
from datetime import datetime, UTC
from itertools import groupby

import geopandas as gpd
import pandas as pd
import requests
import shapely
import yaml
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import substring

from lib.database import get_conn
from lib.logger import configure_logging

# Configure logging
configure_logging(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

COLUMNS = ['zone', 'trail_index', 'source', 'osm_way_id', 'highway', 'balisage', 'etiq_num', 'length_m', 'osm_tags',
           'geometry', 'insert_datetime_utc']


# Fetch the OSM ways of the given highway types in the polygon's bounding box
def fetch_osm_ways(urls, highway, polygon) -> gpd.GeoDataFrame:
    min_lon, min_lat, max_lon, max_lat = polygon.bounds
    query = f"[out:json][timeout:90];way[highway~'^({'|'.join(highway)})$']" \
            f"({min_lat},{min_lon},{max_lat},{max_lon});out tags geom;"
    # Instances are often overloaded: try each in turn, three times over
    for url in urls * 3:
        try:
            response = requests.post(url, data={'data': query}, headers={'User-Agent': 'sports-insert-trails'},
                                     timeout=(10, 100))
            response.raise_for_status()
            ways = response.json()['elements']
            break
        except requests.RequestException as e:
            LOGGER.warning(f'Overpass failed at {url}: {e}')
    else:
        raise ConnectionError('Could not fetch OSM ways from any Overpass instance')
    return gpd.GeoDataFrame(
        [{'osm_way_id': w['id'], 'highway': w['tags']['highway'], 'osm_tags': json.dumps(w['tags'], ensure_ascii=False)}
         for w in ways],
        geometry=[LineString([(p['lon'], p['lat']) for p in w['geometry']]) for w in ways],
        crs=4326,
    )


# Keep the lines inside the area, one row per part
def clip_lines(gdf, area) -> gpd.GeoDataFrame:
    gdf = gdf.clip(area).explode(index_parts=False)
    return gdf[gdf.geometry.geom_type == 'LineString'].reset_index(drop=True)


if __name__ == '__main__':

    # Create argument parser
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--zone', '-z', type=str, required=True, help='Zone to build, as named in the trails config')
    parser.add_argument('--conf', '-c', type=str, help='Path to YAML file containing the trails config')
    parser.add_argument('--secrets', '-s', type=str, help='Path to YAML file containing secrets')
    parser.add_argument('--dry-run', '-d', action='store_true', help='Log the network built, without storing it')

    # Parse arguments & load configuration files
    args = parser.parse_args()
    conf = yaml.safe_load(open(args.conf or 'conf/trails.yaml'))
    secrets = yaml.safe_load(open(args.secrets or 'conf/secrets.yaml'))
    assert args.zone in conf['zones'], f"Unknown zone {args.zone}, add its polygon under 'zones' in the trails config"

    # Work in metres, in the UTM zone of the polygon
    polygon = Polygon(conf['zones'][args.zone])
    crs = gpd.GeoSeries([polygon], crs=4326).estimate_utm_crs()
    area = gpd.GeoSeries([polygon], crs=4326).to_crs(crs).iloc[0]

    # Fetch OSM trails and park marked trails
    osm = clip_lines(fetch_osm_ways(conf['overpass_urls'], conf['highway'], polygon).to_crs(crs), area)
    LOGGER.info(f'Found {len(osm)} OSM ways, {osm.length.sum() / 1000:.1f} km')
    response = requests.get(conf['park_url'])
    response.raise_for_status()
    park = clip_lines(gpd.GeoDataFrame.from_features(response.json(), crs=4326)[['balisage', 'etiq_num', 'geometry']]
                      .to_crs(crs), area)
    LOGGER.info(f'Found {len(park)} park marked trails, {park.length.sum() / 1000:.1f} km')

    # Cut OSM ways into pieces of about piece_length
    pieces = []
    for way in osm.itertuples():
        n = max(1, round(way.geometry.length / conf['piece_length']))
        for i in range(n):
            start, end = way.geometry.length * i / n, way.geometry.length * (i + 1) / n
            pieces.append({'way': way.Index, 'start': start, 'end': end, 'geometry': substring(way.geometry, start, end)})
    pieces = gpd.GeoDataFrame(pieces, crs=crs)

    # Mark each piece like the park trail it overlaps most, if that covers at least half of it
    park_buffers = park.buffer(conf['tolerance'])
    candidates = gpd.sjoin(pieces, gpd.GeoDataFrame(park[['balisage', 'etiq_num']], geometry=park_buffers),
                           predicate='intersects')
    candidates['overlap'] = [pieces.geometry[i].intersection(park_buffers[j]).length
                             for i, j in zip(candidates.index, candidates.index_right)]
    # and if it runs along it: the first metres of a way branching off a marked trail lie within tolerance of it too
    candidates['span'] = [abs(park.geometry[j].project(Point(pieces.geometry[i].coords[0]))
                              - park.geometry[j].project(Point(pieces.geometry[i].coords[-1])))
                          for i, j in zip(candidates.index, candidates.index_right)]
    best = candidates[(candidates.overlap >= candidates.length / 2)
                      & (candidates.span >= conf['min_span'] * candidates.length)] \
        .sort_values('overlap').groupby(level=0).tail(1)
    pieces[['balisage', 'etiq_num']] = best[['balisage', 'etiq_num']].reindex(pieces.index).fillna('')

    # Merge back consecutive pieces of a way with the same marking
    trails = []
    for way, way_pieces in groupby(pieces.itertuples(), key=lambda p: p.way):
        runs = [[mark, list(run)] for mark, run in groupby(way_pieces, key=lambda p: (p.balisage, p.etiq_num))]
        # Mark short gaps between two runs with the same marking, left by switchbacks the park trail cuts through
        for k in range(1, len(runs) - 1):
            if runs[k][0] == ('', '') and runs[k - 1][0] == runs[k + 1][0] \
                    and runs[k][1][-1].end - runs[k][1][0].start <= conf['max_gap']:
                runs[k][0] = runs[k - 1][0]
        for (balisage, etiq_num), group in groupby(runs, key=lambda r: r[0]):
            group = list(group)
            trails.append({
                'source': 'osm',
                'osm_way_id': osm.osm_way_id[way],
                'highway': osm.highway[way],
                'balisage': balisage or None,
                'etiq_num': etiq_num or None,
                'osm_tags': osm.osm_tags[way],
                'geometry': substring(osm.geometry[way], group[0][1][0].start, group[-1][1][-1].end),
            })

    # Add the park trails missing from OSM
    missing = park.assign(geometry=park.difference(osm.buffer(conf['tolerance']).union_all())).explode(index_parts=False)
    for trail in missing[missing.length >= conf['min_park_length']].itertuples():
        trails.append({'source': 'park', 'balisage': trail.balisage, 'etiq_num': trail.etiq_num,
                       'geometry': trail.geometry})

    # Shape rows for the trails table
    trails = gpd.GeoDataFrame(trails, crs=crs)
    trails['zone'] = args.zone
    trails['trail_index'] = range(len(trails))
    trails['osm_way_id'] = trails.osm_way_id.astype('Int64')
    trails['length_m'] = trails.length.round(1)
    trails['insert_datetime_utc'] = datetime.now(UTC)
    trails = pd.DataFrame(trails.drop(columns='geometry')) \
        .assign(geometry=shapely.to_geojson(trails.to_crs(4326).geometry.values))
    marked = trails.balisage.notna()
    LOGGER.info(f'Built {len(trails)} trails, {trails.length_m.sum() / 1000:.1f} km, '
                f'of which {trails.length_m[marked].sum() / 1000:.1f} km marked by the park '
                f'and {trails.length_m[trails.source == "park"].sum() / 1000:.1f} km missing from OSM')

    # Replace the zone's trails in a single transaction
    if not args.dry_run:
        creds_db = {k: v for k, v in secrets['db'].items() if k != 'schema'}
        with get_conn(**creds_db) as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM trails.trail WHERE zone = '{args.zone}';")
            cur.copy_expert(f"COPY trails.trail ({', '.join(COLUMNS)}) FROM STDIN WITH (FORMAT csv)",
                            io.StringIO(trails[COLUMNS].to_csv(index=False, header=False)))
        LOGGER.info(f'Stored {len(trails)} trails for zone {args.zone}')

    LOGGER.info('Done.')
