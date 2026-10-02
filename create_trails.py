import geopandas as gpd
import osmnx as ox
import polyline
import yaml
from shapely.geometry import Polygon, LineString

from lib.strava import Strava

# Read configuration files
secrets = yaml.safe_load(open('conf/secrets.yaml'))

# Log into Strava
strava = Strava(secrets['strava'])
strava.login()

# 1. Define the target area using your coordinates (Lon, Lat)
coords = [
    (5.3386259, 43.2152561),
    (5.3409863, 43.2120032),
    (5.3671130, 43.2060660),
    (5.4043871, 43.2120698),
    (5.4093867, 43.2166832),
    (5.4051166, 43.2214995),
    (5.4018035, 43.2238951),
    (5.3971010, 43.2286821),
    (5.3990582, 43.2346760),
    (5.3984678, 43.2360426),
    (5.3973845, 43.2373962),
    (5.3959254, 43.2380058),
    (5.3931359, 43.2368490),
    (5.3899816, 43.2378182),
    (5.3803589, 43.2378520),
    (5.3678724, 43.2332330),
    (5.3665656, 43.2319751),
    (5.3660077, 43.2274567),
    (5.3616518, 43.2308651),
    (5.3503784, 43.2335033),
    (5.3443149, 43.2253374),
    (5.3386373, 43.2152650)
]
calanques_poly = Polygon(coords)

# ==========================================
# STEP 1: Fetch OSM Trails
# ==========================================
print("Fetching OSM trails...")
# We filter for paths, footways, and tracks
tags = {'highway': ['path', 'footway', 'track']}

# Fetch features inside the polygon
osm_trails = ox.features.features_from_polygon(calanques_poly, tags=tags)

# Filter out polygons (like plazas) to only keep LineStrings (the actual trails)
osm_trails = osm_trails[osm_trails.geometry.type.isin(['LineString', 'MultiLineString'])]

# Convert to a projected Coordinate Reference System (EPSG:2154 is for France)
# This is CRITICAL so we can calculate distances and buffers in meters, not degrees!
osm_trails = osm_trails.to_crs(epsg=2154)

# ==========================================
# STEP 2: Fetch Strava Segments
# ==========================================
print("Fetching Strava Segments...")
# Strava expects a bounding box (south, west, north, east)
min_lon, min_lat, max_lon, max_lat = calanques_poly.bounds

segments_data = strava.segments(min_lat, min_lon, max_lat, max_lon)

# Convert Strava data into a GeoDataFrame
strava_lines = []
for segment in segments_data:
    # Decode the polyline string into (Lat, Lon) points, then swap to (Lon, Lat) for mapping
    points = polyline.decode(segment['points'])
    lon_lat_points = [(p[1], p[0]) for p in points]

    strava_lines.append({
        'segment_id': segment['id'],
        'name': segment['name'],
        'geometry': LineString(lon_lat_points)
    })

strava_gdf = gpd.GeoDataFrame(strava_lines, crs="EPSG:4326")

# Project Strava segments to the same French CRS
strava_gdf = strava_gdf.to_crs(epsg=2154)


# ==========================================
# STEP 3: The Cross-Reference (Map Matching)
# ==========================================
print("Matching OSM to Strava...")
# We add a 20-meter "buffer" around the Strava segments to account for GPS drift
strava_gdf['geometry'] = strava_gdf['geometry'].buffer(20)

# Check which OSM trails intersect with our buffered Strava segments
# Spatial join: keeps OSM trails that intersect the Strava buffers
popular_trails = gpd.sjoin(osm_trails, strava_gdf, how='inner', predicate='intersects')

# Drop duplicates (in case one OSM trail intersects multiple segments)
popular_trails = popular_trails.drop_duplicates(subset=osm_trails.index.name if osm_trails.index.name else 'geometry')

# Now you have 'popular_trails', which contains only the OSM geometries
# that are heavily trafficked by Strava runners!
print(f"Found {len(osm_trails)} total OSM segments.")
print(f"Filtered down to {len(popular_trails)} popular segments.")


