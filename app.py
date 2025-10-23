import streamlit as st
import tempfile
import os
from dxf_generator import generate_dxf

st.set_page_config(page_title="YPA Site Info DXF Generator", layout="centered")

st.title("📐 YPA Vicinity Map DXF Generator")

# --- User inputs ---
project_name = st.text_input("Project Name", "2025-214-003")
northing = st.number_input("Northing (Y)", value=6964000.000, format="%.3f")
easting = st.number_input("Easting (X)", value=2462000.000, format="%.3f")
buffer_miles = st.number_input("Buffer Distance (miles)", value=0.25, format="%.2f")

# County scale factors (example values)
county_scale_factors = {
    "Collin": 1.000152710,
    "Dallas": 1.000145050,
    "Tarrant": 1.000136220,
    "Denton": 1.000155420,
    "Grayson": 1.000168450,
    "Rockwall": 1.000147320,
}

county_name = st.selectbox("Select County", list(county_scale_factors.keys()), index=0)

use_surface_scaling = st.radio("Scale Drawing to Surface?", ["No (Grid)", "Yes (Surface)"]) == "Yes (Surface)"
scale_factor = county_scale_factors[county_name]

drawing_scale = st.selectbox(
    "Select Drawing Scale (1\"=X ft)",
    [1, 10, 20, 30, 40, 50, 60, 80, 100, 150, 200, 500],
    index=9,
)

text_plot_height = st.number_input("Text Plot Height (ft)", value=8.0)
font_choice = st.selectbox("Font Choice", ["ROMANS.SHX", "SIMPLEX.SHX", "TXT.SHX"])

# --- Generate DXF button ---
if st.button("Generate DXF File", key="generate_dxf_button"):
    with st.spinner("Generating DXF... please wait"):
        try:
            tmp_dir = tempfile.mkdtemp()
            nad_suffix = "N83S" if use_surface_scaling else "N83G"

            dxf_file = generate_dxf(
                output_path=tmp_dir,
                project_name=project_name,
                northing=northing,
                easting=easting,
                drawing_scale=drawing_scale,
                text_plot_height=text_plot_height,
                font_choice=font_choice,
                buffer_miles=buffer_miles,
                scale_factor=scale_factor,
                county_name=county_name,
                use_surface_scaling=use_surface_scaling,
                nad_suffix=nad_suffix
            )

            with open(dxf_file_


