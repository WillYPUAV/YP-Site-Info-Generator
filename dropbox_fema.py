import geopandas as gpd
import os
import zipfile
import requests

# ======================================================
# FEMA Dropbox links (replace with your own)
# ======================================================
county_flood_links = {
    "Tarrant": "https://www.dropbox.com/scl/fi/w8ram3nwrdmtqp8m3e4cd/Tarrant_County_FEMA_FLD.zip?rlkey=9tchpzon9ivoflzo12bl59mze&st=2lkdjdn7&dl=1",
    "Dallas":  "https://www.dropbox.com/scl/fi/t6ohze36h97ek85thyt8b/Dallas_County_FEMA_FLD.zip?rlkey=9fv9opzqv21kgn46pwt9najjw&st=vbfbnin2&dl=1",
    "Denton":  "https://www.dropbox.com/scl/fi/66ytkpholqrnsxdaqmbo8/Denton_County_FEMA_FLD.zip?rlkey=j7ls7tezrp2q15vji199aqpnf&st=w4sz8srw&dl=1",
    "Wise":    "https://www.dropbox.com/scl/fi/55t6v87kze3d3yepxymgc/Wise_County_FEMA_FLD.zip?rlkey=v93lsuwl8zvo0f60o1smvoazm&st=sdfpiruy&dl=1",
    "Collin":  "https://www.dropbox.com/scl/fi/jfru49it7ugl0lwpkies7/Collin_County_FEMA_FLD.zip?rlkey=bqbpftrlggeqzomoz7yingnsa&st=fwlg4qfj&dl=1",
    "Johnson": "https://www.dropbox.com/scl/fi/vo914joe5mgqcv7egu9oi/Johnson_County_FEMA_FLD.zip?rlkey=41j6ynytr2mwbshocbar6chmj&st=h4pg9xny&dl=1",
    "Kaufman": "https://www.dropbox.com/scl/fi/8dlwpc3qdbriy3vdam547/Kaufman_County_FEMA_FLD.zip?rlkey=xj7ux7vydo7wihifuv2se5wdp&st=hs3u287z&dl=1",
    "Parker":  "https://www.dropbox.com/scl/fi/8o55x2s8ex74il655x5zy/Parker_County_FEMA_FLD.zip?rlkey=nkgx7o3qm51rf58t406xuufb4&st=q3rld990&dl=1",
    "Rockwall":"https://www.dropbox.com/scl/fi/iaruoc6pxwucrln7bz620/Rockwall_County_FEMA_FLD.zip?rlkey=xnj2ctmrp0sax5n9jlhw14k5s&st=n58be64c&dl=1",
    "Ellis":   "https://www.dropbox.com/scl/fi/7l6pux5z5sut94ho2jxin/Ellis_County_FEMA_FLD.zip?rlkey=vr942erfw4bqzvsj5hybm63r7&st=7lhuldlm&dl=1",
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
