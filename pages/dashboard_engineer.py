import os
from io import BytesIO
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import folium
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from utils.data_handler import read_database, write_database
from utils.ui_helpers import apply_global_styles

# Apply global styles
apply_global_styles()

def render():
    if not st.session_state.get("Engineer_authenticated"):
        st.warning("You must log in as Engineer to access this page.")
        if st.button("Return to Login", key="engineer_goto_login"):
            st.session_state["current_form"] = "Engineer"
            st.rerun()
        return

    st.title("🧑‍🏭 Engineer Dashboard")
    st.write("Welcome, Engineer!")

    # Logout Button
    if st.button("Logout", key="engineer_logout_btn"):
        st.session_state["Engineer_authenticated"] = False
        st.session_state["user_role"] = None
        st.session_state["refresh_trigger"] = not st.session_state.get("refresh_trigger", False)
        st.rerun()

    # Navigation Options
    nav_options = ["Create New Project", "View Project Updates and Reports"]
    selected_option = st.selectbox("Select an Option", nav_options, key="engineer_nav")

    if selected_option == "Create New Project":
        create_new_project()
    elif selected_option == "View Project Updates and Reports":
        view_existing_projects()


def view_existing_projects():
    st.subheader("View Existing Projects")
    database = read_database()

    if not database:
        st.info("No projects found.")
        return

    search_query = st.text_input("Search Projects by Name or ID:", key="engineer_search_query").strip().lower()
    filtered_projects = [
        project for project in database
        if search_query in project["project_name"].lower() or search_query in project["project_id"].lower()
    ] if search_query else database

    if not filtered_projects:
        st.warning("No projects match your search query.")
        return

    for project in filtered_projects:
        with st.expander(f"Project: {project['project_name']} (ID: {project['project_id']})"):
            st.write(f"**Constructor**: {project['constructor']}")
            st.write(f"**Layers**: {', '.join(project['layers'])}")
            st.write(f"**Total Distance**: {project['total_distance_km']} km")
            st.write(f"**Time Required**: {project['time_required_months']} months")
            st.write(f"**Location**: {project['location']}")

            updates = project.get("updates", [])
            if updates:
                st.write("### Updates Summary")
                display_updates_summary(updates)

                st.write("### Visualization")
                visualize_project_updates(updates, project_id=project['project_id'])

                # Generate PDF Report
                pdf_buffer = generate_pdf_stream(project)
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_buffer,
                    file_name=f"{project['project_name']}_report.pdf",
                    mime="application/pdf",
                    key=f"dl_pdf_{project['project_id']}"
                )
            else:
                st.info("No updates available for this project.")


def display_updates_summary(updates):
    # Batch-Level Summary Table
    st.write("### Batch-Level Summary Table")
    batch_df = pd.DataFrame(updates)
    cols_to_show = [c for c in ["batch_number", "layer", "confidence", "distance_covered", "start_coordinates", "end_coordinates"] if c in batch_df.columns]
    st.dataframe(batch_df[cols_to_show])

    # Layer-Wise Aggregated Table
    st.write("### Layer-Wise Aggregated Table")
    batch_df_clean = batch_df.copy()
    if "confidence" in batch_df_clean.columns:
        if batch_df_clean["confidence"].dtype == object:
            batch_df_clean["confidence_num"] = pd.to_numeric(batch_df_clean["confidence"].astype(str).str.rstrip('%'), errors="coerce")
        else:
            batch_df_clean["confidence_num"] = pd.to_numeric(batch_df_clean["confidence"], errors="coerce")
    else:
        batch_df_clean["confidence_num"] = 0.0

    layer_agg_df = batch_df_clean.groupby("layer").agg(
        total_distance=("distance_covered", "sum"),
        avg_confidence=("confidence_num", "mean")
    ).reset_index()
    layer_agg_df["avg_confidence"] = layer_agg_df["avg_confidence"].map(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
    st.dataframe(layer_agg_df)

    # Coordinate Details Table
    st.write("### Coordinate Details Table")
    coord_cols = [c for c in ["batch_number", "start_coordinates", "end_coordinates", "layer"] if c in batch_df.columns]
    st.dataframe(batch_df[coord_cols])


def visualize_project_updates(updates, project_id="default"):
    df = pd.DataFrame(updates)

    # Ensure "batch_number" and "date" columns are of correct types
    if "batch_number" in df.columns:
        df["batch_number"] = pd.to_numeric(df["batch_number"], errors="coerce").fillna(0).astype(int)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Ensure "confidence" is numeric and handle percentages if present
    if "confidence" in df.columns:
        if df["confidence"].dtype == object:
            df["confidence_num"] = pd.to_numeric(df["confidence"].astype(str).str.rstrip("%"), errors="coerce")
        else:
            df["confidence_num"] = pd.to_numeric(df["confidence"], errors="coerce")
    else:
        df["confidence_num"] = 0.0

    # Drop rows with invalid or missing data in critical columns
    clean_cols = [c for c in ["batch_number", "date", "confidence_num", "distance_covered", "start_coordinates", "end_coordinates"] if c in df.columns]
    df_clean = df.dropna(subset=clean_cols)

    if df_clean.empty:
        st.info("No complete data records available for visualization.")
        return

    # Cumulative Distance Coverage Over Time
    st.write("### Cumulative Distance Coverage Over Time")
    df_clean = df_clean.sort_values(by="date")
    df_clean["cumulative_distance"] = df_clean["distance_covered"].cumsum()
    fig1, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df_clean["date"], df_clean["cumulative_distance"], marker="o", linestyle="-", color="#1f77b4")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Distance Covered (meters)")
    ax.set_title("Cumulative Distance Coverage Over Time")
    fig1.autofmt_xdate()
    st.pyplot(fig1)
    plt.close(fig1)

    # Confidence Distribution by Layer
    st.write("### Confidence Distribution by Layer")
    avg_confidence = df_clean.groupby("layer")["confidence_num"].mean().reset_index()
    fig2 = px.bar(
        avg_confidence,
        x="layer",
        y="confidence_num",
        labels={"confidence_num": "Average Confidence (%)", "layer": "Predicted Layer"},
        title="Confidence Distribution by Layer",
        color="layer"
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Batch-Wise Distance Coverage
    st.write("### Batch-Wise Distance Coverage")
    fig3 = px.bar(
        df_clean,
        x="batch_number",
        y="distance_covered",
        labels={"batch_number": "Batch Number", "distance_covered": "Distance Covered (meters)"},
        title="Batch-Wise Distance Coverage",
        color="layer"
    )
    st.plotly_chart(fig3, use_container_width=True)

    # Spatial Progress Map
    st.write("### Spatial Progress Map")
    valid_coordinates = df_clean.dropna(subset=["start_coordinates", "end_coordinates"])
    if not valid_coordinates.empty:
        map_cache_key = f"cached_spatial_map_{project_id}"
        map_ = create_spatial_progress_map(valid_coordinates)
        st.session_state[map_cache_key] = map_._repr_html_()
        st.components.v1.html(st.session_state[map_cache_key], height=500, scrolling=True)
    else:
        st.info("No valid coordinates available for mapping.")


def create_spatial_progress_map(valid_coordinates):
    """Create a Folium map with start and end coordinates."""
    map_center = valid_coordinates["start_coordinates"].iloc[0]
    map_ = folium.Map(location=map_center, zoom_start=18)

    for _, row in valid_coordinates.iterrows():
        folium.Marker(
            location=row["start_coordinates"],
            popup=f"Start Batch {row['batch_number']} - {row.get('layer', '')}",
            icon=folium.Icon(color="green", icon="play")
        ).add_to(map_)
        folium.Marker(
            location=row["end_coordinates"],
            popup=f"End Batch {row['batch_number']} - {row.get('layer', '')}",
            icon=folium.Icon(color="red", icon="stop")
        ).add_to(map_)
        folium.PolyLine(
            locations=[row["start_coordinates"], row["end_coordinates"]],
            color="blue",
            weight=4,
            opacity=0.7
        ).add_to(map_)

    return map_


def generate_pdf_stream(project):
    """Generate a PDF report for the project."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, 750, f"Project Report: {project.get('project_name', 'N/A')}")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, 730, f"Project ID: {project.get('project_id', 'N/A')}")
    pdf.drawString(50, 712, f"Constructor: {project.get('constructor', 'N/A')}")
    pdf.drawString(50, 694, f"Location: {project.get('location', 'N/A')}")
    pdf.drawString(50, 676, f"Total Distance: {project.get('total_distance_km', 'N/A')} km")
    pdf.drawString(50, 658, f"Time Required: {project.get('time_required_months', 'N/A')} months")
    pdf.drawString(50, 638, "Updates:")

    y = 618
    for update in project.get("updates", []):
        if y < 100:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = 750
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(70, y, f"- Batch Number: {update.get('batch_number', 'N/A')}, Date: {update.get('date', 'N/A')}")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(90, y - 16, f"Predicted Layer: {update.get('layer', 'N/A')} (Confidence: {update.get('confidence', 'N/A')})")
        pdf.drawString(90, y - 32, f"Distance Covered: {update.get('distance_covered', 0):.2f} meters")
        pdf.drawString(90, y - 48, f"Start Coordinates: {update.get('start_coordinates', 'N/A')}")
        pdf.drawString(90, y - 64, f"End Coordinates: {update.get('end_coordinates', 'N/A')}")
        y -= 84

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


def create_new_project():
    st.subheader("Create New Project")
    constructor_name = st.text_input("Constructor Name", key="constructor_name")
    project_name = st.text_input("Project Name", key="project_name")
    project_id = st.text_input("Project ID", key="project_id")
    layers = st.multiselect(
        "Select which layers to be applied",
        options=[
            "Site Preparation",
            "Base and Sub-base Preparation",
            "Utility and Drainage Installation",
            "Surface Preparation",
            "Asphalt Laying and Finishing",
        ],
        key="layers",
    )
    total_distance = st.number_input(
        "Total Distance of the Road to be Constructed (in kilometers)",
        min_value=0.1,
        step=0.1,
        key="total_distance",
    )
    time_required = st.number_input(
        "Time Required to Complete the Project (in Months)",
        min_value=1,
        step=1,
        key="time_required",
    )
    start_location = st.text_input("Location Start (From)", key="start_location")
    end_location = st.text_input("Location End (To)", key="end_location")

    if st.button("Submit Project", key="submit_new_project_btn"):
        if not project_name.strip() or not project_id.strip():
            st.error("Please fill in all the required fields!")
        elif not layers:
            st.error("Please select at least one layer.")
        elif not start_location.strip() or not end_location.strip():
            st.error("Please fill in the start and end locations.")
        else:
            database = read_database()
            # Check if project_id already exists
            if any(p["project_id"] == project_id.strip() for p in database):
                st.error(f"A project with ID '{project_id}' already exists!")
                return
            new_project = {
                "constructor": constructor_name.strip(),
                "project_name": project_name.strip(),
                "project_id": project_id.strip(),
                "layers": layers,
                "total_distance_km": total_distance,
                "time_required_months": time_required,
                "location": f"{start_location.strip()} to {end_location.strip()}",
                "updates": [],
            }
            database.append(new_project)
            write_database(database)
            st.success(f"Project '{project_name}' created successfully!")
            st.rerun()

if __name__ == "__main__":
    render()
