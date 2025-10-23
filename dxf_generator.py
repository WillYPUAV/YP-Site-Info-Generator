import os
import math
import zipfile
import tempfile
import warnings
import geopandas as gpd
import osmnx as ox
import ezdxf
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from dropbox_fema import get_fema_zip

# Silence common warnings
warnings.filterwarnings("ignore", message=".*Shell empty after removing invalid points.*")

def generate_dxf(
    output_path,
    project_name,
    northing,
    easting,
    drawing_scale,
    text_plot_height,
    font_choice,
    buffer_miles,
    scale_factor,
    county_name,
    use_surface_scaling,
    nad_suffix
):
    """
    Generates DXF with OSM roads, project boundary, and FEMA flood layers.
    """

    print(f"🧭 Generating DXF for {project_name} in {county_name} County...")

    CRS_NAD83 = "EPSG:2276"  # Example: Texas North Central
    BUFFER_FEET = buffer_miles * 5280.0
    BUFFER_METERS = BUFFER_FEET * 0.3048  # for OSM (WGS84 meters)

    # --- Create AOI ---
    center = Point(float(easting), float(northing))
    aoi = gpd.GeoSeries([center.buffer(BUFFER_FEET)], crs=CRS_NAD83)
    print(f"📏 Buffer: {BUFFER_FEET:.2f} ft | Scale: 1\"={drawing_scale} ft")

    # --- Get OSM roads ---
    try:
        center_latlon = gpd.GeoSeries([center], crs=CRS_NAD83).to_crs("EPSG:4326").iloc[0]
        ox.settings.log_console = False
        ox.settings.use_cache = True
        roads = ox.graph_from_point((center_latlon.y, center_latlon.x), dist=BUFFER_METERS, network_type="drive")
        edges = ox.graph_to_gdfs(roads, nodes=False, edges=True)
        edges = edges.to_crs(CRS_NAD83)
        edges = gpd.overlay(edges, gpd.GeoDataFrame(geometry=aoi), how="intersection")
        edges = edges.drop_duplicates(subset="name").dropna(subset=["name"])
        print(f"✅ {len(edges)} unique named roads added.")
    except Exception as e:
        print(f"⚠️ Failed to load OSM roads: {e}")
        edges = gpd.GeoDataFrame(columns=["geometry", "name"], crs=CRS_NAD83)

    # --- Load FEMA Flood Data ---
    fema = None
    fema_path = get_fema_zip(county_name)
    if fema_path:
        try:
            fema = gpd.read_file(fema_path)
            if not fema.empty:
                fema = fema.to_crs(CRS_NAD83)
                fema = gpd.overlay(fema, gpd.GeoDataFrame(geometry=aoi), how="intersection")
                print(f"🌊 FEMA data clipped for {county_name}")
            else:
                print(f"⚠️ FEMA shapefile is empty for {county_name}")
        except Exception as e:
            print(f"⚠️ Failed to load FEMA data: {e}")

    # --- Create DXF ---
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()

    # Layers
    doc.layers.add("BOUNDARY", color=2)
    doc.layers.add("TEXT", color=7)
    doc.layers.add("ROADS", color=6)
    doc.layers.add("FEMA", color=4)

    # Fonts
    if "romans" in font_choice.lower():
        font_file = "romans.shx"
    elif "simplex" in font_choice.lower():
        font_file = "simplex.shx"
    else:
        font_file = "txt.shx"
    doc.styles.new("YPA_FONT", dxfattribs={"font": font_file})

    # --- Draw boundary ---
    poly = aoi.geometry.iloc[0]
    if isinstance(poly, Polygon):
        msp.add_lwpolyline(list(poly.exterior.coords), close=True, dxfattribs={"layer": "BOUNDARY"})
        print("🟡 Project boundary drawn.")

    # --- Add roads ---
    for _, row in edges.iterrows():
        geom = row.geometry
        name = str(row.get("name", "")).strip()
        if geom.is_empty or not name:
            continue
        coords = list(geom.coords) if geom.geom_type == "LineString" else None
        if coords:
            msp.add_lwpolyline(coords, dxfattribs={"layer": "ROADS"})
            midpt = coords[len(coords)//2]
            text = msp.add_text(name, dxfattribs={"height": text_plot_height * 0.8, "layer": "TEXT", "style": "YPA_FONT"})
            text.dxf.insert = midpt

    # --- Add FEMA polygons ---
    if fema is not None and not fema.empty:
        for _, row in fema.iterrows():
            geom = row.geometry
            if geom.is_empty:
                continue
            if geom.geom_type == "Polygon":
                msp.add_lwpolyline(list(geom.exterior.coords), close=True, dxfattribs={"layer": "FEMA"})
            elif geom.geom_type == "MultiPolygon":
                for part in geom.geoms:
                    msp.add_lwpolyline(list(part.exterior.coords), close=True, dxfattribs={"layer": "FEMA"})
        print("✅ FEMA flood polygons added.")

    # --- Apply surface scale ---
    if use_surface_scaling:
        print(f"📐 Applying scale factor {scale_factor} for surface coordinates.")
        for e in msp.query("LWPOLYLINE"):
            pts = [(x * scale_factor, y * scale_factor) for x, y, *_ in e.get_points()]
            e.set_points(pts)
        nad_suffix = "N83S"
    else:
        nad_suffix = "N83G"

    # --- Add annotation text ---
    label_text = f"{project_name}\n{county_name} County\nScale 1\"={drawing_scale} ft"
    note = msp.add_text(label_text, dxfattribs={"height": text_plot_height, "layer": "TEXT", "style": "YPA_FONT"})
    note.dxf.insert = (easting, northing + BUFFER_FEET / 2)

    # --- Save file ---
    filename = f"{project_name}_{county_name}_VicinityMap_1in{drawing_scale}ft_{nad_suffix}.dxf"
    dxf_path = os.path.join(output_path, filename)
    doc.saveas(dxf_path)
    print(f"✅ DXF saved: {filename}")

    return dxf_path
