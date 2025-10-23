import os
import math
import zipfile
import tempfile
import warnings
import geopandas as gpd
import osmnx as ox
import ezdxf
from shapely.geometry import Point, Polygon, LineString, MultiPolygon, MultiLineString
from dropbox_fema import get_fema_zip

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
    print(f"🧭 Generating DXF for {project_name} in {county_name} County...")

    CRS_NAD83 = "EPSG:2276"  # Texas North Central (ft)
    CRS_WGS84 = "EPSG:4326"
    BUFFER_FEET = buffer_miles * 5280.0
    BUFFER_METERS = BUFFER_FEET * 0.3048

    center = Point(float(easting), float(northing))
    buffer_gdf = gpd.GeoDataFrame(geometry=[center.buffer(BUFFER_FEET)], crs=CRS_NAD83)

    # ======================================================
    # 🛣️ Load OSM roads
    # ======================================================
    try:
        center_latlon = gpd.GeoSeries([center], crs=CRS_NAD83).to_crs(CRS_WGS84).iloc[0]
        G = ox.graph_from_point((center_latlon.y, center_latlon.x), dist=BUFFER_METERS, network_type="drive")
        edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
        edges = edges.to_crs(CRS_NAD83)
        roads = gpd.clip(edges, buffer_gdf)
        roads = roads.dropna(subset=["name"]).drop_duplicates(subset="name")
        print(f"✅ {len(roads)} named roads loaded.")
    except Exception as e:
        print(f"⚠️ OSM roads failed: {e}")
        roads = gpd.GeoDataFrame(columns=["geometry", "name"], crs=CRS_NAD83)

    # ======================================================
    # 🌊 Load FEMA flood data (from ZIP)
    # ======================================================
    fema = None
    fema_zip_path = get_fema_zip(county_name)
    if fema_zip_path and os.path.exists(fema_zip_path):
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(fema_zip_path, "r") as zip_ref:
                    zip_ref.extractall(tmpdir)

                # find the first shapefile in the extracted folder
                shp_files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.lower().endswith(".shp")]
                if shp_files:
                    shp_path = shp_files[0]
                    print(f"📂 FEMA shapefile found: {os.path.basename(shp_path)}")
                    fema = gpd.read_file(shp_path)
                    fema = fema.to_crs(CRS_NAD83)
                    fema = gpd.clip(fema, buffer_gdf)
                    print(f"✅ FEMA flood polygons loaded and clipped for {county_name}")
                else:
                    print(f"⚠️ No .shp file found in FEMA ZIP for {county_name}")
        except Exception as e:
            print(f"⚠️ FEMA extraction or read failed: {e}")
    else:
        print("⚠️ FEMA ZIP not found in Dropbox or missing path reference")

    # ======================================================
    # ✏️ Create DXF file
    # ======================================================
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()

    # Layers
    doc.layers.add("BOUNDARY", color=2)
    doc.layers.add("TEXT", color=7)
    doc.layers.add("ROADS", color=6)
    doc.layers.add("FEMA", color=4)

    # Fonts
    font_file = "romans.shx" if "romans" in font_choice.lower() else (
        "simplex.shx" if "simplex" in font_choice.lower() else "txt.shx"
    )
    doc.styles.new("YPA_FONT", dxfattribs={"font": font_file})

    # ======================================================
    # 🟡 Project boundary
    # ======================================================
    poly = buffer_gdf.geometry.iloc[0]
    if isinstance(poly, Polygon):
        msp.add_lwpolyline(list(poly.exterior.coords), close=True, dxfattribs={"layer": "BOUNDARY"})

    # ======================================================
    # 🚗 Draw roads
    # ======================================================
    for _, row in roads.iterrows():
        geom = row.geometry
        name = str(row.get("name", "")).strip()
        if geom.is_empty or not name:
            continue

        if geom.geom_type == "LineString":
            coords = list(geom.coords)
            msp.add_lwpolyline(coords, dxfattribs={"layer": "ROADS"})
            midpt = coords[len(coords)//2]
            txt = msp.add_text(name, dxfattribs={"height": text_plot_height * 0.8, "layer": "TEXT", "style": "YPA_FONT"})
            txt.dxf.insert = midpt

        elif geom.geom_type == "MultiLineString":
            for part in geom.geoms:
                coords = list(part.coords)
                msp.add_lwpolyline(coords, dxfattribs={"layer": "ROADS"})

    # ======================================================
    # 🌊 Draw FEMA polygons
    # ======================================================
    if fema is not None and not fema.empty:
        zone_field = next((f for f in ["FLD_ZONE", "ZONE_SUBTY", "ZONE"] if f in fema.columns), None)
        for _, row in fema.iterrows():
            geom = row.geometry
            if geom.is_empty:
                continue

            if isinstance(geom, Polygon):
                msp.add_lwpolyline(list(geom.exterior.coords), close=True, dxfattribs={"layer": "FEMA"})
                if zone_field:
                    zone = str(row.get(zone_field, "")).strip()
                    if zone:
                        c = geom.centroid
                        label = msp.add_text(zone, dxfattribs={"height": text_plot_height * 0.7, "layer": "TEXT", "style": "YPA_FONT"})
                        label.dxf.insert = (c.x, c.y)

            elif isinstance(geom, MultiPolygon):
                for part in geom.geoms:
                    msp.add_lwpolyline(list(part.exterior.coords), close=True, dxfattribs={"layer": "FEMA"})
        print("🌊 FEMA polygons drawn.")

    # ======================================================
    # 📏 Surface scaling
    # ======================================================
    if use_surface_scaling:
        print(f"📐 Applying scale factor {scale_factor}")
        for entity in msp.query("LWPOLYLINE"):
            pts = [(x * scale_factor, y * scale_factor) for x, y, *_ in entity.get_points()]
            entity.set_points(pts)
        nad_suffix = "N83S"
    else:
        nad_suffix = "N83G"

    # ======================================================
    # 📝 Project info label
    # ======================================================
    info = f"{project_name}\n{county_name} County\nScale 1\"={drawing_scale} ft"
    note = msp.add_text(info, dxfattribs={"height": text_plot_height, "layer": "TEXT", "style": "YPA_FONT"})
    note.dxf.insert = (easting, northing + BUFFER_FEET / 2)

    # ======================================================
    # 💾 Save DXF
    # ======================================================
    filename = f"{project_name}_{county_name}_VicinityMap_1in{drawing_scale}ft_{nad_suffix}.dxf"
    out_path = os.path.join(output_path, filename)
    doc.saveas(out_path)
    print(f"✅ DXF saved successfully: {filename}")

    return out_path


    return dxf_path
