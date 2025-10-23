# app.py
import streamlit as st
from dxf_generator import generate_dxf
import tempfile
import os

st.set_page_config(page_title="YPA Vicinity Map Generator", layout="centered")
st.title("📍 YPA Vicinity Map Generator")

with st.form("inputs"):
    project_name = st.text_input("Project Name")
    county_name = st.text_input("County Name (for label or FEMA reference)")

    northing = st.number_input("Grid Northing (ft)", value=6963281.3, format="%.3f")
    easting = st.number_input("Grid Easting (ft)", value=2466606.4, format="%.3f")

    buffer_miles = st.number_input("Buffer Distance (miles)", value=3.0, min_value=0.1, max_value=10.0, step=0.5)

    scale = st.selectbox(
        "Drawing Scale (1\" = ?')",
        [1, 10, 20, 30, 40, 50, 60, 80, 100, 150, 200, 500],
        index=8,  # default 1"=100'
    )

    text_height = st.number_input("Text Height (inches)", value=0.08)
    font = st.selectbox("Font", ["simplex", "romans", "calibri", "arial", "times"])

    submitted = st.form_submit_button("Generate DXF")

if submitted:
    st.info("Generating DXF... please wait ⏳")

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
            )

            st.success(f"✅ DXF created successfully: {dxf_name}")
            st.download_button("⬇️ Download DXF", open(output_path, "rb"), file_name=dxf_name)
        except Exception as e:
            st.error(f"❌ Error: {e}")
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
