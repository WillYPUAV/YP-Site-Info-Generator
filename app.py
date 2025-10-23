import streamlit as st
import os
from dxf_generator import generate_dxf

# ======================================================
# Streamlit Page Setup
# ======================================================
st.set_page_config(
    page_title="YPA DXF Vicinity Map Generator",
    layout="centered",
    page_icon="📐"
)

st.title("📐 YPA Vicinity Map DXF Generator")
st.write("Generate DXF vicinity maps with labeled roads and FEMA floodlines automatically.")

# ======================================================
# User Input Section
# ======================================================

st.subheader("📍 Project Information")
project_name = st.text_input("Project Name (e.g., 2025-214-003)", "")
northing = st.number_input("Grid Northing (ft)", value=6963281.3, step=0.1, format="%.2f")
easting = st.number_input("Grid Easting (ft)", value=2466606.4, step=0.1, format="%.2f")

# --- Drawing scale dropdown ---
st.subheader("📏 Drawing Scale and Text Settings")
scale_options = [1, 10, 20, 30, 40, 50, 60, 80, 100, 150, 200, 500]
drawing_scale = st.selectbox("Select Drawing Scale (1\" = X')", options=scale_options, index=8)

text_plot_height = st.number_input("Text Height on Plot (inches)", value=0.08, step=0.01)
font_choice = st.selectbox("Font Choice", ["simplex", "romans", "arial", "calibri"])

# --- Buffer distance ---
buffer_miles = st.number_input("Buffer Distance (miles from coordinate)", value=3.0, step=0.5)

# ======================================================
# County and Surface Scaling Options
# ======================================================

st.subheader("🏛 County and Coordinate Basis")

# Common counties you work in
county_options = [
    "Collin", "Dallas", "Tarrant", "Denton", "Grayson", "Rockwall", "Hunt", "Cooke", "Fannin"
]
county_name = st.selectbox("Select County", options=county_options, index=0)

# Scale factors (example values — update as needed)
county_scale_factors = {
    "Collin": 1.000152710,
    "Dallas": 1.000130050,
    "Tarrant": 1.000121980,
    "Denton": 1.000149320,
    "Grayson": 1.000160220,
    "Rockwall": 1.000141800,
    "Hunt": 1.000168950,
    "Cooke": 1.000174000,
    "Fannin": 1.000165000
}

apply_surface = st.radio("Scale to Surface?", ["No (Grid)", "Yes (Surface)"], index=0)

if apply_surface.startswith("Yes"):
    coord_basis = "Surface"
    scale_factor = county_scale_factors.get(county_name, 1.000150000)
    nad_suffix = "N83S"
else:
    coord_basis = "Grid"
    scale_factor = 1.0
    nad_suffix = "N83G"

# ======================================================
# Generate DXF Button
# ======================================================

st.subheader("⚙️ Generate DXF File")

if st.button("🚀 Generate Vicinity Map"):
    if not project_name:
        st.error("❌ Please enter a project name before generating.")
    else:
        st.info("⏳ Generating DXF... This may take a minute.")

        dxf_file = f"{project_name}_{county_name}_VicinityMap_1in{drawing_scale}ft_{nad_suffix}.dxf"

        try:
            generate_dxf(
                output_path=dxf_file,
                project_name=project_name,
                northing=northing,
                easting=easting,
                drawing_scale=drawing_scale,
                text_plot_height=text_plot_height,
                font_choice=font_choice,
                buffer_miles=buffer_miles,
                county_name=county_name,
                coord_basis=coord_basis,
                scale_factor=scale_factor,
                nad_suffix=nad_suffix
            )

            st.success(f"✅ DXF created successfully: {dxf_file}")

            if os.path.exists(dxf_file):
                with open(dxf_file, "rb") as f:
                    st.download_button(
                        "⬇️ Download DXF",
                        f,
                        file_name=dxf_file,
                        mime="application/dxf",
                        key=f"download_{dxf_file}"  # 🔑 Unique key fix
                    )
        except Exception as e:
            st.error(f"⚠️ Error: {e}")

# ======================================================
# Footer
# ======================================================
st.write("---")
st.caption("Developed by Yazel Peebles & Associates, LLC | Automated DXF Map Generator © 2025")

