import streamlit as st
from dxf_generator import generate_dxf

st.set_page_config(page_title="YPA Site Info Generator", layout="centered")

st.title("📍 YPA Site Info Generator")

project_name = st.text_input("Project Name", "")
northing = st.number_input("Grid Northing (ft)", value=0)
easting = st.number_input("Grid Easting (ft)", value=0)
buffer_miles = st.number_input("Buffer Distance (miles)", value=3.0)

county = st.selectbox("Select County", [
    "Tarrant", "Dallas", "Denton", "Collin", "Johnson",
    "Wise", "Rockwall", "Kaufman", "Parker", "Ellis"
])

scale = st.selectbox('Drawing Scale (1"=)', [1,10,20,30,40,50,60,80,100,150,200,500])
coord_basis = st.radio("Coordinate Basis", ["Grid (N83G)", "Surface (N83S)"])
scale_factor = 1.000152710 if "Surface" in coord_basis else 1.0
nad_suffix = "N83S" if "Surface" in coord_basis else "N83G"
font_choice = st.selectbox("Font", ["simplex", "romans", "arial", "calibri"])
text_height_in = 0.08

if st.button("Generate DXF"):
    st.write("⏳ Generating DXF...")
    dxf_file = f"{project_name}_{county}_VicinityMap_1in{scale}ft_{nad_suffix}.dxf"
    generate_dxf(
        output_path=dxf_file,
        project_name=project_name,
        northing=northing,
        easting=easting,
        drawing_scale=scale,
        text_plot_height=text_height_in,
        font_choice=font_choice,
        buffer_miles=buffer_miles,
        county_name=county,
        coord_basis=coord_basis,
        scale_factor=scale_factor,
        nad_suffix=nad_suffix
    )
    st.success("✅ DXF created successfully!")
    with open(dxf_file, "rb") as f:
        st.download_button("⬇️ Download DXF", f, file_name=dxf_file, mime="application/dxf")

        st.download_button("⬇️ Download DXF", f, file_name=dxf_file, mime="application/dxf")
