import os
import math
import zipfile
import tempfile
import warnings
import geopandas as gpd
import ezdxf
from shapely.geometry import Point, LineString, MultiLineString, Polygon
from shapely.ops import unary_union, linemerge
from dropbox_fema import get_fema_zip

# Ignore geometry warnings from Shapely
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
    Generates a DXF vicinity map with FEMA flood layers if available.
    """

    print(f"🧭 Generating DXF for {project_name} in {county_name} County...")

    # Define constants
    CRS_NAD83 = "EPSG:2276"  # Texas North Central (example)
    BUFFER_FEET = buffer_miles * 5280.0

    # --- Create point and buffer area ---
    center = Point(float(easting), float(northing))
    buffer_area = gpd.GeoSeries([center.buffer(BUFFER_FEET)], crs=CRS_NAD83)
    print(f"📏 Buffer size: {BUFFER_FEET:.2f} ft")

    # --- Download and read FEMA flood layer ---
    fema_path = get_fema_zip(county_name)
    fema = None

    if fema_path:
        try:
            fema = gpd.read_file(fema_path)
            if not fema.empty:
                fema = fema.to_crs(CRS_NAD83)
                fema = gpd.overlay(fema, gpd.GeoDataFrame(geometry=buffer_area), how="intersection")
                print(f"✅ FEMA polygons loaded and clipped for {county_name}")
            else:
                print(f"⚠️ FEMA file for {county_name} is empty or invalid")
        except Exception as e:
            print(f"⚠️ Failed to load FEMA data: {e}")
    else:
        print(f"⚠️ No FEMA shapefile found for {county_name}")

    # --- Create DXF document ---
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()

    # Add layers
    doc.layers.add("BOUNDARY", color=2)   # Yellow
    doc.layers.add("TEXT", color=7)       # White
    doc.layers.add("FEMA", color=4)       # Cyan

    # Add text style
    if "romans" in font_choice.lower():
        font_file = "romans.shx"
    elif "simplex" in font_choice.lower():
        font_file = "simplex.shx"
    else:
        font_file = "txt.shx"
    doc.styles.new("YPA_FONT", dxfattribs={"font": font_file})

    # --- Draw project buffer boundary ---
    boundary = buffer_area.geometry.iloc[0]
    if isinstance(boundary, Polygon):
        coords = list(boundary.exterior.coords)
        msp.add_lwpolyline(coords, close=True, dxfattribs={"layer": "BOUNDARY"})
        print("🟡 Added project boundary to DXF")

    # --- Draw FEMA polygons (if any) ---
    if fema is not None and not fema.empty:
        for _, row in fema.iterrows():
            geom = row.geometry
            if geom.is_empty:
                continue
            if isinstance(geom, Polygon):
                exterior = list(geom.exterior.coords)
                msp.add_lwpolyline(exterior, close=True, dxfattribs={"layer": "FEMA"})
            elif geom.geom_type == "MultiPolygon":
                for part in geom.geoms:
                    exterior = list(part.exterior.coords)
                    msp.add_lwpolyline(exterior, close=True, dxfattribs={"layer": "FEMA"})
        print("🌊 FEMA flood polygons added to DXF")

    # --- Scale coordinates if using surface ---
    if use_surface_scaling:
        print(f"📐 Applying surface scale factor: {scale_factor}")
        for entity in msp.query("LWPOLYLINE"):
            scaled_points = [(x * scale_factor, y * scale_factor) for x, y, *_ in entity.get_points()]
            entity.set_points(scaled_points)
        nad_suffix = "N83S"
    else:
        nad_suffix = "N83G"

    # --- Add text annotation ---
    text = msp.add_text(
        f"{project_name}\n{county_name} County\nScale 1\"={drawing_scale} ft",
        dxfattribs={
            "height": text_plot_height,
            "layer": "TEXT",
            "style": "YPA_FONT"
        }
    )
    # Fix: set text insertion manually
    try:
        text.set_pos((easting, northing + (BUFFER_FEET / 2)))
    except AttributeError:
        text.dxf.insert = (easting, northing + (BUFFER_FEET / 2))

    print("📝 Added text annotation")

    # --- Save DXF ---
    filename = f"{project_name}_{county_name}_VicinityMap_1in{drawing_scale}ft_{nad_suffix}.dxf"
    output_file = os.path.join(output_path, filename)
    doc.saveas(output_file)
    print(f"✅ DXF saved successfully: {filename}")

    return output_file
