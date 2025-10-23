import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point, LineString, MultiLineString
from shapely.ops import unary_union, linemerge
import ezdxf, math, re
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

    # --- Font map ---
    font_map = {
        "simplex": "simplex.shx",
        "romans": "romans.shx",
        "arial": "arial.ttf",
        "calibri": "calibri.ttf"
    }
    font_name = font_map.get(font_choice.lower(), "simplex.shx")
    model_height = text_plot_height * drawing_scale
    style_name = f"{font_choice.upper()}_STYLE"

    # --- AOI ---
    pt = gpd.GeoDataFrame(geometry=[Point(easting, northing)], crs=crs_nad83)
    buffer_distance = buffer_miles * 1609.34
    buffer_geom = pt.to_crs(epsg=3857).buffer(buffer_distance).to_crs(crs_nad83)
    lat, lon = pt.to_crs(epsg=4326).geometry.y.iloc[0], pt.to_crs(epsg=4326).geometry.x.iloc[0]

    # --- Download roads ---
    try:
        G = ox.graph_from_point((lat, lon), dist=buffer_distance, network_type="drive")
    except Exception:
        G = ox.graph_from_point((lat, lon), dist=buffer_distance, network_type="all")

    edges = ox.graph_to_gdfs(G, nodes=False, edges=True).to_crs(crs_nad83)
    edges = gpd.clip(edges, buffer_geom)
    edges["label"] = edges["name"].apply(lambda x: "Unnamed" if not isinstance(x, str) else x)
    edges = edges[edges["label"] != "Unnamed"].copy()

    # --- Merge same-named roads ---
    merged = []
    for name, group in edges.groupby("label"):
        combined = unary_union(group.geometry)
        if isinstance(combined, (LineString, MultiLineString)):
            merged.append({"label": name, "geometry": linemerge(combined)})
    roads = gpd.GeoDataFrame(merged, crs=crs_nad83)

    # --- Scale for surface ---
    if coord_basis.lower().startswith("surface"):
        def scale_geom(g):
            if g.geom_type == "LineString":
                return LineString([(x * scale_factor, y * scale_factor) for x, y in g.coords])
            elif g.geom_type == "MultiLineString":
                return MultiLineString([LineString([(x * scale_factor, y * scale_factor) for x, y in p.coords]) for p in g.geoms])
            return g
        roads["geometry"] = roads["geometry"].apply(scale_geom)

    # --- DXF setup ---
    doc = ezdxf.new("R2018")
    if not doc.styles.has_entry(style_name):
        doc.styles.new(style_name, dxfattribs={"font": font_name})
    msp = doc.modelspace()
    doc.layers.new("ROADS", dxfattribs={"color": 7})
    doc.layers.new("ROAD_LABELS", dxfattribs={"color": 2})
    doc.layers.new("FEMA_FLOODLINES", dxfattribs={"color": 1})

    # --- Helper for label orientation ---
    def true_bearing(p1, p2):
        dx, dy = p2.x - p1.x, p2.y - p1.y
        return math.degrees(math.atan2(dy, dx)) % 360

    def upright_rotation(line):
        start, end = Point(line.coords[0]), Point(line.coords[-1])
        ang = true_bearing(start, end)
        return ang + 180 if 90 < ang <= 270 else ang

    # --- Draw roads ---
    for _, row in roads.iterrows():
        geom, name = row.geometry, row["label"]
        coords = list(geom.coords)
        msp.add_lwpolyline(coords, dxfattribs={"layer": "ROADS"})
        mid = geom.interpolate(0.5, normalized=True)
        rot = upright_rotation(geom)
        msp.add_text(name, dxfattribs={"height": model_height, "rotation": rot, "layer": "ROAD_LABELS", "style": style_name}).set_dxf_attrib("insert", (mid.x, mid.y))

    # --- FEMA Floodlines ---
    fema = load_fema_layer(county_name)
    if fema is not None:
        fema = fema.to_crs(crs_nad83)
        fema_clip = gpd.clip(fema, buffer_geom)
        for geom in fema_clip.geometry:
            if geom.is_empty:
                continue
            if geom.geom_type == "LineString":
                msp.add_lwpolyline(list(geom.coords), dxfattribs={"layer": "FEMA_FLOODLINES"})
            elif geom.geom_type == "MultiLineString":
                for seg in geom.geoms:
                    msp.add_lwpolyline(list(seg.coords), dxfattribs={"layer": "FEMA_FLOODLINES"})

    # --- Save DXF ---
    safe_name = re.sub(r'[<>:\"/\\|?*]', '_', project_name)
    county_tag = f"_{county_name.strip().title()}" if county_name else ""
    out_dxf = f"{safe_name}{county_tag}_VicinityMap_1in{drawing_scale}ft_{nad_suffix}.dxf"
    doc.saveas(output_path)
    print(f"✅ DXF saved: {output_path}")
    return out_dxf

