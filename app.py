# app.py
import streamlit as st
from dxf_generator import generate_dxf
import tempfile, os

st.set_page_config(page_title="YPA Vicinity Map Generator", layout="centered")
st.title("📍 YPA Vicinity Map Generator")

# County options with known scale factors
county_scale_factors = {
    "Collin": 1.000152710,
    "Dallas": 1.000136506,
    "Denton": 1.000150630,
    "Ellis": 1.000072449,
    "Johnson": 1.00012,
    "Kaufman": 1.000114077,
    "Parker": 1.00012,
    "Rockwall": 1.000146135,
    "Tarrant": 1.00012,
    "Wise": 1.00012,
}

with st.form("inputs"):
    project_name = st.text_input("Project Name")

    county_name = st.selectbox(
        "Select County",
        list(county_scale_factors.keys()),
        index=3  # default Tarrant
    )

    northing = st.number_input("Grid Northing (ft)", value=6963281.3, format="%.3f")
    easting = st.number_input("Grid Easting (ft)", value=2466606.4, format="%.3f")

    buffer_miles = st.number_input("Buffer Distance (miles)", value=3.0, min_value=0.1, max_value=10.0, step=0.5)

    scale = st.selectbox(
        "Drawing Scale (1\" = ?')",
        [1, 10, 20, 30, 40, 50, 60, 80, 100, 150, 200, 500],
        index=8,
    )

    surface_toggle = st.selectbox("Apply Surface Scaling?", ["No", "Yes"])
    text_height = st.number_input("Text Height (inches)", value=0.08)
    font = st.selectbox("Font", ["simplex", "romans", "calibri", "arial", "times"])

    submitted = st.form_submit_button("Generate DXF")

if submitted:
    st.info("Generating DXF... please wait ⏳")

    if surface_toggle == "Yes":
        coord_basis = "Surface"
        scale_factor = county_scale_factors[county_name]
        suffix = "N83S"
    else:
        coord_basis = "Grid"
        scale_factor = 1.0
        suffix = "N83G"

    st.write(f"📐 Coordinate Basis: **{coord_basis}** | Scale Factor: **{scale_factor:.9f}**")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        output_path = tmp.name
        try:
            dxf_name = generate_dxf(
                output_path=output_path,
                project_name=project_name,
                northing=northing,
                easting=easting,
                drawing_scale=scale,
                text_plot_height=text_height,
                font_choice=font,
                buffer_miles=buffer_miles,
                county_name=county_name,
                coord_basis=coord_basis,
                scale_factor=scale_factor,
                nad_suffix=suffix,  # NEW
            )

            st.success(f"✅ DXF created successfully: {dxf_name}")
            st.download_button("⬇️ Download DXF", open(output_path, "rb"), file_name=dxf_name)
        except Exception as e:
            st.error(f"❌ Error: {e}")
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
