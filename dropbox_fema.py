import geopandas as gpd
import requests, tempfile, zipfile, io, os
from county_flood_links import county_flood_links

def load_fema_layer(county):
    if county not in county_flood_links:
        print(f"⚠️ No FEMA shapefile found for {county}")
        return None

    url = county_flood_links[county]
    print(f"⬇️ Downloading FEMA shapefile for {county}...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            r = requests.get(url, timeout=60)
            r.raise_for_status()

            # Handle ZIP or single file
            if url.endswith(".zip?dl=1"):
                with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                    zf.extractall(tmpdir)
                    shp_files = [os.path.join(tmpdir, f) for f in zf.namelist() if f.endswith(".shp")]
                    if shp_files:
                        gdf = gpd.read_file(shp_files[0])
                    else:
                        raise ValueError("No .shp file found in zip")
            else:
                shp_path = os.path.join(tmpdir, f"{county}.shp")
                with open(shp_path, "wb") as f:
                    f.write(r.content)
                gdf = gpd.read_file(shp_path)

            print(f"✅ Loaded FEMA flood data for {county} ({len(gdf)} features)")
            return gdf

    except Exception as e:
        print(f"⚠️ Failed to load FEMA data: {e}")
        return None
