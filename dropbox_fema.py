import geopandas as gpd
import os
import zipfile
import requests

# ======================================================
# FEMA Dropbox links (replace with your own)
# ======================================================
county_flood_links = {
    "Collin": "https://www.dropbox.com/scl/fi/abcd1234/Collin_FEMA_FloodLines.zip?dl=1",
    "Dallas": "https://www.dropbox.com/scl/fi/efgh5678/Dallas_FEMA_FloodLines.zip?dl=1",
    "Tarrant": "https://www.dropbox.com/scl/fi/ijkl9012/Tarrant_FEMA_FloodLines.zip?dl=1",
    # Add more as needed...
}

# ======================================================
# FEMA loader function
# ======================================================
def load_fema_layer(county_name, buffer_geom=None, crs="EPSG:6584"):
    """
    Loads FEMA floodlines for the selected county.
    - First tries to load from local /content/fema_data/
    - If not found, downloads the ZIP from Dropbox automatically
    - Converts polygons to boundary lines
    - Clips to AOI buffer if provided
    """

    base_dir = "/content/fema_data"
    os.makedirs(base_dir, exist_ok=True)

    local_zip = os.path.join(base_dir, f"{county_name}_FEMA_FloodLines.zip")
    local_shp = os.path.join(base_dir, f"{county_name}_FEMA_FloodLines.shp")

    try:
        # -----------------------------------------------
        # STEP 1: Check local shapefile first
        # -----------------------------------------------
        if os.path.exists(local_shp):
            print(f"📁 Found local FEMA shapefile for {county_name}")
            fema = gpd.read_file(local_shp).to_crs(crs)

        # -----------------------------------------------
        # STEP 2: Download from Dropbox if not local
        # -----------------------------------------------
        else:
            url = county_flood_links.get(county_name)
            if not url:
                print(f"⚠️ No Dropbox link found for {county_name}")
                return None

            print(f"⬇️ Downloading FEMA flood data for {county_name}...")
            r = requests.get(url)
            r.raise_for_status()
            with open(local_zip, "wb") as f:
                f.write(r.content)

            # Extract shapefile components
            with zipfile.ZipFile(local_zip, "r") as zip_ref:
                zip_ref.extractall(base_dir)

            # Find extracted .shp file
            shp_candidates = [f for f in os.listdir(base_dir) if f.endswith(".shp") and county_name in f]
            if not shp_candidates:
                print(f"⚠️ No .shp file found after extracting {local_zip}")
                return None

            shp_path = os.path.join(base_dir, shp_candidates[0])
            fema = gpd.read_file(shp_path).to_crs(crs)

        # -----------------------------------------------
        # STEP 3: Convert polygons → boundary lines
        # -----------------------------------------------
        if fema.geom_type.isin(["Polygon", "MultiPolygon"]).any():
            print("🔄 Converting FEMA polygons to boundary lines...")
            fema["geometry"] = fema.boundary

        # -----------------------------------------------
        # STEP 4: Clip to AOI buffer (optional)
        # -----------------------------------------------
        if buffer_geom is not None:
            try:
                fema = gpd.clip(fema, buffer_geom)
            except Exception as e:
                print(f"⚠️ FEMA clip failed: {e}")

        # -----------------------------------------------
        # STEP 5: Cleanup and return
        # -----------------------------------------------
        fema = fema[~fema.is_empty & fema.is_valid]
        print(f"✅ Loaded {len(fema)} FEMA flood features for {county_name}")
        return fema

    except Exception as e:
        print(f"⚠️ Error loading FEMA data for {county_name}: {e}")
        return None
        print(f"⚠️ Error loading FEMA data for {county_name}: {e}")
        return None
