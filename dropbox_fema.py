import requests
import tempfile
import os

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
    """Downloads FEMA shapefile ZIP for a given county."""
    url = county_flood_links.get(county_name)
    if not url:
        return None

    try:
        tmp_zip = os.path.join(tempfile.gettempdir(), f"{county_name}.zip")
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(tmp_zip, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return tmp_zip
    except Exception as e:
        print(f"⚠️ Failed to download FEMA data: {e}")
        return None
