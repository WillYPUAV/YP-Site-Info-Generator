import streamlit as st
from dxf_generator import generate_dxf
import tempfile
import os

# --- Streamlit page config ---
st.set_page_config(page_title="YPA Site Info DXF Generator", layout="centered")

# --- App title ---
st.title("📐 YPA Vicinity Map & DXF Generator")
st.write("Automatically generate labeled DXF files with scaled coordinates and optional FEMA flood data.")

# --- County scale factors (grid to surface) ---
county_scale_factors = {
    "Tarrant": 1.00015271,
    "Dallas": 1.00015887,
    "Collin": 1.00016044,
    "Denton": 1.00015129,
    "Johnson": 1.00015085,
    "Parker": 1.00014523,
    "Ellis": 1.00016284,
    "Kaufman": 1.00016547,
    "Rockwall": 1.00016219,
}

# --- Input fields ---
project_name = st.text_input("Project Name", "2025-214-003 Vicinity Map")
northing = st.number_input("Northing (ft, NAD83)", value=6964250.00)
easting = st.number_input("Easting (ft, NAD83)", value=2462290.00)
buffer_miles = st.number_input("Buffer distance (miles)", value=1.0, step=0.25)

county_name = st.selectbox(
    "Select County",
    list(county_scale_factors.keys()),
    index=0
)

scale_to_surface = st.radio(
    "Scale drawing to surface?",
    ["No (Grid)", "Yes (Surface)"],
    horizontal=True
)

drawing_scale = st.selectbox(
    "Drawing Scale (1\" = __ ft)",
    [1, 10, 20, 30, 40, 50, 60, 80, 100, 150, 200, 500],
    index=10
)

text_height = st.number_input("Text Height (ft)", value=8.0)
font_choice = st.selectbox("Font", ["simplex.shx", "romans.shx", "arial.ttf"])

# --- Output filename suffix ---
if scale_to_surface == "Yes (Surface)":
    nad_suffix = "N83S"
    scale_factor = county_scale_factors[county_name]
else:
    nad_suffix = "N83G"
    scale_factor = 1.0

# --- Run DXF generation ---
if st.button("🚀 Generate DXF"):
    with st.spinner("Processing... generating DXF file..."):
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dxf_file = os.path.join(tmpdir, f"{project_name}_{nad_suffix}.dxf")

                # Call the generator function
                generate_dxf(
                    output_path=dxf_file,
                    project_name=project_name,
                    northing=northing,
                    easting=easting,
                    drawing_scale=drawing_scale,
                    text_plot_height=text_height,
                    font_choice=font_choice,
                    buffer_miles=buffer_miles,
                    scale_factor=scale_factor,
                    nad_suffix=nad_suffix,
                    county_name=county_name
                )

                # Show success
                st.success(f"✅ DXF generated successfully: {os.path.basename(dxf_file)}")

                # Download button (with unique key)
                with open(dxf_file, "rb") as f:
                    st.download_button(
                        "⬇️ Download DXF File",
                        f,
                        file_name=os.path.basename(dxf_file),
                        mime="application/dxf",
                        key="download_dxf_button"
                    )

        except Exception as e:
            st.error(f"⚠️ An error occurred: {e}")

