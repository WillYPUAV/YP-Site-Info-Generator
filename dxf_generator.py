import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point, LineString, MultiLineString
from shapely.ops import unary_union, linemerge
import ezdxf
import math, re
from dropbox_fema import load_fema_layer

def generate_dxf(
    output_path,
    project_name,
    northing,
    easting,
    drawing_scale,
    text_plot_height,
    font_choice,
    buffer_miles=3.0,
    county_name="",
    coord_basis="Grid",
    scale_factor=1.0,
    nad_suffix="N83G"
):
    crs_nad83 = "EPSG:6584"  # NAD83(2011) / Texas Zone 4202 (ftUS)
    font_map = {"simplex": "simplex.shx", "romans": "romans.shx", "arial": "arial.ttf", "calibri": "calibri.ttf"}
    font_name = font_map.get(font_choice.lower(), "simplex.shx")
    model_height = text_plot_height * drawing_scale
    style_name = f"{font_choice.upper()}_STYLE"

    # --- Create AOI buffer ---
    pt = gpd.GeoDataFrame(geometry=[Point(easting, northing)], crs=crs_nad83)
    buffer_distance = buffer_miles * 1609.34
    buffer_geom = pt.to_crs(epsg=3857).buffer(buffer_distance).to_crs(crs_nad83)
    pt_wgs84 = pt.to_crs(epsg=4326)
    lat, lon = pt_wgs84.geometry.y.iloc[0], pt_wgs84.geometry.x.iloc[0]

    # --- Get OSM roads ---
    try:
        G = ox.graph_from_point((lat, lon), dist=buffer_distance, network_type="drive")
    except Exception:
        G = ox.graph_from_point((lat, lon), dist=buffer_distance, network_type="all")
    edges = ox
