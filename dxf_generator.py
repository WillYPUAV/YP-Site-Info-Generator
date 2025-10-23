# dxf_generator.py
import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point, LineString, MultiLineString
from shapely.ops import unary_union, linemerge
import ezdxf
import math, re

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
    """
    Generates a DXF vicinity map from OpenStreetMap road data.
    Supports Grid vs Surface scaling using a county-specific scale factor.

    Parameters
    ----------
    output_path : str
        Temporary file path to save DXF.
    project_name : str
        Project identifier.
    northing, easting : float
        NAD83(2011) coordinates of project center in US Survey Feet.
    drawing_scale : int
        Drawing scale (e.g. 100 for 1"=100').
    text_plot_height : float
        Annotative text height in inches.
    font_choice : str
        Selected font name.
    buffer_miles : float
        Buffer radius in miles from project coordinate.
    county_name : str
        County for labeling.
    coord_basis : str
        "Grid" or "Surface".
    scale_factor : float
        Combined Scale Factor (for surface scaling).
    nad_suffix : str
        "N83G" or "N83S" appended to DXF filename.
    """

    crs_nad83 = "EPSG:6584"  # NAD83(2011) / Texas Zone 4202 (ftUS)

    # --- Font setup ---
    font_map = {
        "simplex": "simplex.shx",
        "romans": "romans.shx",
        "arial": "arial.ttf",
        "calibri": "calibri.ttf",
        "times": "times.ttf",
    }
    font_name = font_map.get(font_choice.lower(), "simplex.shx")
    model_height = text_plot_height * drawing_scale
    style_name = f"{font_choice.upper()}_STYLE"

    # --- AOI setup ---
    pt = gpd.GeoDataFrame(geometry=[Point(easting, northing)], crs=crs_nad83)
    buffer_distance = buffer_miles * 1609.34  # miles → meters
    buffer_geom = pt.to_crs(epsg=3857).buffer(buffer_distance).to_crs(crs_nad83)
    pt_wgs84 = pt.to_crs(epsg=4326)
    lat, lon = pt_wgs84.geometry.y.iloc[0], pt_wgs84.geometry.x.iloc[0]

    # --- Download roads ---
    try:
        G = ox.graph_from_point((lat, lon), dist=buffer_distance, network_type="all")
    except Exception:
        G = ox.graph_from_point((lat, lon), dist=buffer_distance, network_type="drive")

    edges = ox.graph_to_gdfs(G, nodes=False, edges=True).to_crs(crs_nad83)
    edges = gpd.clip(edges, buffer_geom)

    # --- Clean road names ---
    def normalize_name(name):
        if isinstance(name, list):
            return " / ".join(name)
        elif isinstance(name, str):
            return name
        else:
            return "Unnamed Road"

    edges["label"] = edges["name"].apply(normalize_name)
    edges = edges[edges["label"] != "Unnamed Road"].copy()

    # --- Merge segments with same name ---
    merged_roads = []
    for name, group in edges.groupby("label"):
        combined = unary_union(group.geometry)
        if isinstance(combined, (LineString, MultiLineString)):
            merged = linemerge([combined]) if isinstance(combined, LineString) else linemerge(combined)
            merged_roads.append({"label": name, "geometry": merged})
    roads_gdf = gpd.GeoDataFrame(merged_roads, crs=crs_nad83)

    # --- Apply surface scaling if requested ---
    if coord_basis.lower() == "surface" and abs(scale_factor - 1.0) > 1e-9:
        def scale_geom(geom):
            if geom.is_empty:
                return geom
            if geom.geom_type == "LineString":
                return LineString([(x * scale_factor, y * scale_factor) for x, y in geom.coords])
            elif geom.geom_type == "MultiLineString":
                return MultiLineString([
                    LineString([(x * scale_factor, y * scale_factor) for x, y in part.coords])
                    for part in geom.geoms
                ])
            return geom
        roads_gdf["geometry"] = roads_gdf["geometry"].apply(scale_geom)

    # --- Helper functions ---
    def true_bearing(p1, p2):
        dx, dy = p2.x - p1.x, p2.y - p1.y
        return math.degrees(math.atan2(dy, dx)) % 360

    def upright_rotation(line):
        coords = list(line.coords)
        if len(coords) < 2:
            return 0
        start, end = Point(coords[0]), Point(coords[-1])
        angle = true_bearing(start, end)
        # Flip upside-down text
        if 90 < angle <= 270:
            angle = (angle + 180) % 360
        return angle

    def offset_point(midpoint, rotation_deg, offset_distance=10):
        angle_rad = math.radians(rotation_deg + 90)
        dx = math.cos(angle_rad) * offset_distance
        dy = math.sin(angle_rad) * offset_distance
        return Point(midpoint.x + dx, midpoint.y + dy)

    # --- Build DXF ---
    doc = ezdxf.new("R2018")
    if not doc.styles.has_entry(style_name):
        doc.styles.new(style_name, dxfattribs={"font": font_name})

    msp = doc.modelspace()
    doc.layers.new(name="ROADS", dxfattribs={"color": 7})
    doc.layers.new(name="ROAD_LABELS", dxfattribs={"color": 2})

    for _, row in roads_gdf.iterrows():
        geom = row.geometry
        name = row["label"]

        def draw_line(line):
            coords = list(line.coords)
            msp.add_lwpolyline(coords, dxfattribs={"layer": "ROADS"})
            mid = line.interpolate(0.5, normalized=True)
            rotation = upright_rotation(line)
            label_pt = offset_point(mid, rotation)
            msp.add_text(
                name,
                dxfattribs={
                    "height": model_height,
                    "rotation": rotation,
                    "layer": "ROAD_LABELS",
                    "style": style_name,
                },
            ).set_dxf_attrib("insert", (label_pt.x, label_pt.y))

        if geom.geom_type == "LineString":
            draw_line(geom)
        elif geom.geom_type == "MultiLineString":
            longest = max(geom.geoms, key=lambda g: g.length)
            for seg in geom.geoms:
                msp.add_lwpolyline(list(seg.coords), dxfattribs={"layer": "ROADS"})
            draw_line(longest)

    # --- Save DXF ---
    safe_name = re.sub(r'[<>:\"/\\|?*]', '_', project_name)
    county_tag = f"_{county_name.strip().title()}" if county_name else ""
    out_dxf = f"{safe_name}{county_tag}_VicinityMap_1in{drawing_scale}ft_{nad_suffix}.dxf"
    doc.saveas(output_path)

    return out_dxf
