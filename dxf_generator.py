import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point, LineString, MultiLineString
from shapely.ops import unary_union, linemerge
import ezdxf
import math
import zipfile
import tempfile
from dropbox_fema import get_fema_zip

def generate_dxf(output_path, project_name, northing, easting, drawing_scale,
                 text_plot_height, font_choice, buffer_miles, scale_factor,
                 nad_suffix, county_name):

    # --- Define projection ---
    crs_nad83 = "EPSG:6584"

    # --- Define AOI buffer ---
    center = Point(easting, northing)
    buffer_m = buffer_miles * 1609.34  # miles to meters
    buffer = gpd.GeoSeries([center.buffer(buffer_m)], crs=crs_nad83)
    buffer_path = os.path.join(tempfile.gettempdir(), "aoi.geojson")
    buffer.to_file(buffer_path, driver="GeoJSON")

    print(f"📏 Scale 1\"={drawing_scale}'  Text={text_plot_height} ft  Font={font_choice}")

    # --- OSM Roads ---
    print("🚗 Downloading OpenStreetMap roads...")
    graph = ox.graph_from_point((northing, easting), dist=buffer_m, network_type='drive')
    edges = ox.graph_to_gdfs(graph, nodes=False)[['name', 'geometry']]
    edges = edges.dropna(subset=['name']).drop_duplicates(subset=['name', 'geometry'])
    edges['name'] = edges['name'].str.title()
    print(f"✅ {edges['name'].nunique()} unique named roads")

    # --- Merge road segments ---
    merged = []
    for name, group in edges.groupby("name"):
        combined = unary_union(group.geometry)
        try:
            merged_geom = linemerge(combined)
        except Exception:
            merged_geom = combined
        merged.append({"label": name, "geometry": merged_geom})
    roads = gpd.GeoDataFrame(merged, crs=crs_nad83)

    # --- Apply surface scale factor ---
    if scale_factor != 1.0:
        roads["geometry"] = roads.scale(xfact=scale_factor, yfact=scale_factor, origin=center)
        print(f"🗺️ Applied surface scale factor: {scale_factor}")

    # --- Create DXF document ---
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()

    # --- Setup text style ---
    style_name = f"{font_choice.split('.')[0].upper()}_STYLE"
    if style_name not in doc.styles:
        doc.styles.new(style_name, dxfattribs={"font": font_choice})

    # --- Add roads and labels ---
    for _, row in roads.iterrows():
        geom = row.geometry
        if geom.is_empty:
            continue

        if isinstance(geom, (LineString, MultiLineString)):
            msp.add_lwpolyline(list(geom.coords) if isinstance(geom, LineString)
                               else [p.coords[:] for p in geom.geoms],
                               dxfattribs={"layer": "ROADS"})

            # --- Label Placement ---
            mid = geom.interpolate(0.5, normalized=True)
            angle = math.degrees(math.atan2(geom.coords[-1][1] - geom.coords[0][1],
                                            geom.coords[-1][0] - geom.coords[0][0]))
            readable_angle = angle
            if angle > 90 or angle < -90:
                readable_angle += 180
            msp.add_text(
                row["label"],
                dxfattribs={
                    "style": style_name,
                    "height": text_plot_height * drawing_scale / 100,
                    "rotation": readable_angle,
                    "layer": "ROAD_LABELS"
                }
            ).set_pos((mid.x, mid.y), align="CENTER")

    # --- FEMA Flood Data ---
    try:
        fema_zip = get_fema_zip(county_name)
        if fema_zip:
            print(f"⬇️ Downloading FEMA shapefile for {county_name}...")
            with tempfile.TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(fema_zip, "r") as zf:
                    zf.extractall(tmpdir)
                    shp_files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")]
                    if shp_files:
                        fema = gpd.read_file(shp_files[0])
                        fema = fema.to_crs(crs_nad83)
                        fema = fema.clip(buffer)
                        for _, fl in fema.iterrows():
                            if isinstance(fl.geometry, (LineString, MultiLineString)):
                                msp.add_lwpolyline(list(fl.geometry.coords) if isinstance(fl.geometry, LineString)
                                                   else [p.coords[:] for p in fl.geometry.geoms],
                                                   dxfattribs={"layer": "FEMA"})
            print(f"✅ FEMA floodlines added for {county_name}")
        else:
            print("⚠️ No FEMA data found for this county.")
    except Exception as e:
        print(f"⚠️ FEMA load failed: {e}")

    # --- Save DXF ---
    doc.saveas(output_path)
    print(f"✅ DXF saved successfully: {os.path.basename(output_path)}")
