import os
import requests
import tempfile
import zipfile


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

def get_fema_zip(county_name):
    """
    Downloads and extracts FEMA shapefile for a given county.
    Returns path to the extracted .shp file.
    """
    url = county_flood_links.get(county_name)
    if not url:
        print(f"⚠️ No Dropbox FEMA data link found for {county_name}")
        return None

    try:
        print(f"⬇️ Downloading FEMA shapefile ZIP for {county_name}...")
        r = requests.get(url, stream=True)
        if r.status_code != 200:
            print(f"⚠️ Download failed: {r.status_code}")
            return None

        # Save ZIP temporarily
        tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        for chunk in r.iter_content(1024):
            tmp_zip.write(chunk)
        tmp_zip.close()

        # Extract contents
        tmpdir = tempfile.mkdtemp()
        with zipfile.ZipFile(tmp_zip.name, "r") as z:
            z.extractall(tmpdir)

        # Auto-detect any .shp file inside the ZIP
        shp_files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.lower().endswith(".shp")]
        if not shp_files:
            print(f"⚠️ No .shp file found inside FEMA ZIP for {county_name}")
            return None

        shp_path = shp_files[0]
        print(f"📂 Found shapefile: {os.path.basename(shp_path)}")
        return shp_path

    except Exception as e:
        print(f"⚠️ Dropbox download error: {e}")
        return None
