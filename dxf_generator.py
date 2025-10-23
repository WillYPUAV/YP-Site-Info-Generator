import os
import math
import zipfile
import tempfile
import geopandas as gpd
import osmnx as ox
import ezdxf
from shapely.geometry import Point, LineString, MultiLineString
from shapely.ops import unary_union, linemerge
from shapely.validation import make_valid
from dropbox_fema import get_fema_zip


def generate_dxf(output_path, project_name, northing, easting, drawing_scale,
                 text_plot_height, font_choice, buffer_miles, scale_factor,
                 nad_suffix, county_name):

    # ======================================================
    # 1. Projection and AOI
    # ======================================================
    crs_nad83 = "EPSG:6584"
    center = Point(easting, northing)
    buffer_m = buffer_miles * 1609.34  # miles → meters
    buffer = gpd.GeoSeries([center.buffer(buffer_m)], crs=crs_nad83)
    buffer_path = os.path.join(tempfile.gettempdir(), "aoi.geojson")
    buffer.to_file(buffer_path, driver="GeoJSON")

    print(f"📏 Scale 1\"={drawing_scale}'  Text={text_plot_height} ft  Font={font_choice}")

    # ======================================================
    # 2. OpenStreetMap Roads
    # ======================================================
    print("🚗 Downloading OpenStreetMap roads...")
    graph = ox.graph_from_point((northing, easting), dist=buffer_m, network_type='drive')
    edges = ox.graph_to_gdfs(graph, nodes=False)[['name', 'geometry']]
    edges = edges.dropna(subset=['name']).drop_duplicates(subset=['name', 'geometry'])
    edges['name'] = edges['name'].str.title()
    print(f"✅ {edges['name'].nunique()} unique named roads")

    # Merge road segments
    merged = []
    for name, group in edges.groupby("name"):
        combined = unary_union(group.geometry)
        try:
            merged_geom = linemerge(combined)
        except Exception:
            merged_geom = combined
        merged.append({"label": name, "geometry": merged_geom})
    roads = gpd.GeoDataFrame(merged, crs=crs_nad83)

    # ======================================================
    # 3. Apply Surface Scale Factor
    # ======================================================
    if scale_factor != 1.0:
        roads["geometry"] = roads.scale(xfact=scale_factor, yfact=scale_factor, origin=center)
        print(f"🗺️ Applied surface scale factor: {scale_factor}")

    # ======================================================
    # 4. DXF Setup
    # ======================================================
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()

    # Font fallback logic — avoids DXF font errors
    font_fallbacks = {
        "arial.ttf": "simplex.shx",
        "calibri.ttf": "simplex.shx",
        "times.ttf": "romans.shx"
    }
    font_used = font_fallbacks.get(font_choice.lower(), font_choice)
    style_name = f"{font_used.split('.')[0].upper()}_STYLE"

    if style_name not in doc.styles:
        doc.styles.new(style_name, dxfattribs={"font": font_used})

    # ======================================================
    # 5. Draw Roads and Labels
    # ======================================================
    for _, row in roads.iterrows():
        geom = row.geometry
        if geom.is_empty:
            continue

        if isinstance(geom, (LineString, MultiLineString)):
            # Draw line geometry
            if isinstance(geom, LineString):
                coords = list(geom.coords)
                msp.add_lwpolyline(coords, dxfattribs={"layer": "ROADS"})
            else:
                for part in geom.geoms:
                    msp.add_lwpolyline(list(part.coords), dxfattribs={"layer": "ROADS"})

            # Label Placement
            mid = geom.interpolate(0.5, normalized=True)
            start, end = geom.coords[0], geom.coords[-1]
            angle = math.degrees(math.atan2(end[1] - start[1], end[0] - start[0]))

            # Adjust rotation to keep readable (E/N orientation)
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

    # ======================================================
    # 6. FEMA Floodlines (from Dropbox ZIP)
    # ======================================================
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

                    # Repair invalid geometries
                    before = len(fema)
                    fema["geometry"] = fema["geometry"].apply(lambda g: make_valid(g) if g and not g.is_valid else g)
                    fema = fema[~fema.geometry.is_empty & fema.geometry.notna()]
                    cleaned = before - len(fema)
                    if cleaned > 0:
                        print(f"🧹 Cleaned {cleaned} invalid FEMA geometries")

                    # Clip to AOI
                    try:
                        fema = fema.clip(buffer)
                    except Exception as e:
                        print(f"⚠️ FEMA clipping skipped: {e}")

                    # Draw FEMA lines
                    for _, fl in fema.iterrows():
                        geom = fl.geometry
                        if isinstance(geom, (LineString, MultiLineString)):
                            if isinstance(geom, LineString):
                                msp.add_lwpolyline(list(geom.coords), dxfattribs={"layer": "FEMA"})
                            else:
                                for part in geom.geoms:
                                    msp.add_lwpolyline(list(part.coords), dxfattribs={"layer": "FEMA"})

            print(f"✅ FEMA floodlines added for {county_name}")
        else:
            print("⚠️ No FEMA data found for this county.")
    except Exception as e:
        print(f"⚠️ FEMA load failed: {e}")

    # ======================================================
    # 7. Save DXF
    # ======================================================
    doc.saveas(output_path)
    print(f"✅ DXF saved successfully: {os.path.basename(output_path)}")
