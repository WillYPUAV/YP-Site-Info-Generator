import geopandas as gpd
import os

def load_fema_layer(county_name, buffer_geom=None, crs="EPSG:6584"):
    """
    Loads FEMA floodline shapefile for a given county and clips it to the AOI buffer.
    Expects shapefiles in /content/fema_data/ named like 'Collin_FEMA_FloodLines.shp'
    """

    try:
        # Path to your FEMA shapefile directory
        base_dir = "/content/fema_data"
        fema_file = os.path.join(base_dir, f"{county_name}_FEMA_FloodLines.shp")

        if not os.path.exists(fema_file):
            print(f"⚠️ FEMA shapefile not found for {county_name}: {fema_file}")
            return None

        print(f"📁 Loading FEMA flood data for {county_name}...")
        fema = gpd.read_file(fema_file)

        # Reproject to match NAD83 (2011) Zone 4202 ftUS
        fema = fema.to_crs(crs)

        # Convert polygons to boundary lines if needed
        if fema.geom_type.isin(["Polygon", "MultiPolygon"]).any():
            print("🔄 Converting FEMA polygons to boundary lines...")
            fema["geometry"] = fema.boundary

        # Clip to the AOI buffer if provided
        if buffer_geom is not None:
            try:
                fema = gpd.clip(fema, buffer_geom)
            except Exception as e:
                print(f"⚠️ FEMA clip failed: {e}")

        # Drop empty geometries
        fema = fema[~fema.is_empty & fema.is_valid]

        print(f"✅ Loaded {len(fema)} FEMA flood features for {county_name}")
        return fema

    except Exception as e:
        print(f"⚠️ Error loading FEMA data for {county_name}: {e}")
        return None
