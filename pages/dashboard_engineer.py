import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from utils.data_handler import read_database, write_database
from utils.ui_helpers import apply_global_styles
import plotly.express as px
from streamlit_folium import st_folium
import folium

# Apply global styles
apply_global_styles()


def render():
    if not st.session_state.get("Engineer_authenticated"):
        st.warning("You must log in as Engineer to access this page.")
        return

    st.title("Engineer Dashboard")
    st.write("Welcome, Engineer!")

    # Logout Button
    if st.button("Logout"):
        st.session_state["Engineer_authenticated"] = False
        st.session_state["user_role"] = None
        st.session_state["refresh_trigger"] = not st.session_state.get("refresh_trigger", False)

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
                visualize_project_updates(updates)

                # Generate PDF Report
                if st.button(f"Generate PDF Report for {project['project_name']}", key=f"report_{project['project_id']}"):
                    pdf_buffer = generate_pdf_stream(project)
                    st.download_button(
                        label="Download PDF Report",
                        data=pdf_buffer,
                        file_name=f"{project['project_name']}_report.pdf",
                        mime="application/pdf",
                    )
            else:
                st.info("No updates available for this project.")


def display_updates_summary(updates):
    # Batch-Level Summary Table
    st.write("### Batch-Level Summary Table")
    batch_df = pd.DataFrame(updates)
    st.dataframe(batch_df[["batch_number", "layer", "confidence", "distance_covered", "start_coordinates", "end_coordinates"]])

    # Layer-Wise Aggregated Table
    st.write("### Layer-Wise Aggregated Table")
    layer_agg_df = batch_df.groupby("layer").agg(
        total_distance=("distance_covered", "sum"),
        avg_confidence=("confidence", lambda x: pd.to_numeric(x.str.rstrip('%')).mean())
    ).reset_index()
    st.dataframe(layer_agg_df)

    # Coordinate Details Table
    st.write("### Coordinate Details Table")
    st.dataframe(batch_df[["batch_number", "start_coordinates", "end_coordinates", "layer"]])


def visualize_project_updates(updates):
    df = pd.DataFrame(updates)

    # Ensure "batch_number" and "date" columns are of correct types
    df["batch_number"] = df["batch_number"].astype(int)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Ensure "confidence" is numeric and handle percentages if present
    if "confidence" in df.columns:
        df["confidence"] = pd.to_numeric(df["confidence"].str.rstrip("%"), errors="coerce")

    # Drop rows with invalid or missing data in critical columns
    df = df.dropna(subset=["batch_number", "date", "confidence", "distance_covered", "start_coordinates", "end_coordinates"])

    # Cumulative Distance Coverage Over Time
    st.write("### Cumulative Distance Coverage Over Time")
    df["cumulative_distance"] = df["distance_covered"].cumsum()
    fig1, ax = plt.subplots()
    ax.plot(df["date"], df["cumulative_distance"], marker="o", linestyle="-")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Distance Covered (meters)")
    ax.set_title("Cumulative Distance Coverage Over Time")
    st.pyplot(fig1)

    # Confidence Distribution by Layer
    st.write("### Confidence Distribution by Layer")
    avg_confidence = df.groupby("layer")["confidence"].mean().reset_index()
    fig2 = px.bar(
        avg_confidence,
        x="layer",
        y="confidence",
        labels={"confidence": "Average Confidence (%)", "layer": "Predicted Layer"},
        title="Confidence Distribution by Layer",
    )
    st.plotly_chart(fig2)

    # Batch-Wise Distance Coverage
    st.write("### Batch-Wise Distance Coverage")
    fig3 = px.bar(
        df,
        x="batch_number",
        y="distance_covered",
        labels={"batch_number": "Batch Number", "distance_covered": "Distance Covered (meters)"},
        title="Batch-Wise Distance Coverage",
    )
    st.plotly_chart(fig3)

    # Spatial Progress Map
    st.write("### Spatial Progress Map")
    if not df.empty:
        valid_coordinates = df.dropna(subset=["start_coordinates", "end_coordinates"])

        if not valid_coordinates.empty:
            # Cache the map in session state to prevent blinking
            if "cached_spatial_map_html" not in st.session_state:
                map_ = create_spatial_progress_map(valid_coordinates)
                st.session_state["cached_spatial_map_html"] = map_._repr_html_()
            
            # Display the cached map content
            st.components.v1.html(st.session_state["cached_spatial_map_html"], height=500, scrolling=True)
        else:
            st.info("No valid coordinates available for mapping.")
    else:
        st.info("No data available for visualization.")


def create_spatial_progress_map(valid_coordinates):
    """Create a Folium map with start and end coordinates."""
    map_center = valid_coordinates["start_coordinates"].iloc[0]
    map_ = folium.Map(location=map_center, zoom_start=20)

    for _, row in valid_coordinates.iterrows():
        folium.Marker(
            location=row["start_coordinates"],
            popup=f"Start Batch {row['batch_number']}"
        ).add_to(map_)
        folium.Marker(
            location=row["end_coordinates"],
            popup=f"End Batch {row['batch_number']}"
        ).add_to(map_)
        folium.PolyLine(
            locations=[row["start_coordinates"], row["end_coordinates"]],
            color="blue"
        ).add_to(map_)

    return map_





def generate_pdf_stream(project):
    """Generate a PDF report for the project."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.drawString(50, 750, f"Project Report: {project['project_name']}")
    pdf.drawString(50, 730, f"Project ID: {project['project_id']}")
    pdf.drawString(50, 710, f"Constructor: {project['constructor']}")
    pdf.drawString(50, 690, f"Location: {project['location']}")
    pdf.drawString(50, 670, f"Total Distance: {project['total_distance_km']} km")
    pdf.drawString(50, 650, f"Time Required: {project['time_required_months']} months")
    pdf.drawString(50, 630, "Updates:")

    y = 610
    for update in project["updates"]:
        pdf.drawString(70, y, f"- Batch Number: {update['batch_number']}, Date: {update['date']}")
        pdf.drawString(90, y - 20, f"Predicted Layer: {update['layer']} (Confidence: {update['confidence']})")
        pdf.drawString(90, y - 40, f"Distance Covered: {update['distance_covered']} meters")
        pdf.drawString(90, y - 60, f"Start Coordinates: {update['start_coordinates']}")
        pdf.drawString(90, y - 80, f"End Coordinates: {update['end_coordinates']}")
        y -= 100

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


def create_new_project():
    st.subheader("Create New Project")
    st.text_input("Constructor Name", key="constructor_name")
    st.text_input("Project Name", key="project_name")
    st.text_input("Project ID", key="project_id")
    st.multiselect(
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
    st.number_input(
        "Total Distance of the Road to be Constructed (in kilometers)",
        min_value=0.1,
        step=0.1,
        key="total_distance",
    )
    st.number_input(
        "Time Required to Complete the Project (in Months)",
        min_value=1,
        step=1,
        key="time_required",
    )
    st.text_input("Location Start (From)", key="start_location")
    st.text_input("Location End (To)", key="end_location")

    if st.button("Submit"):
        if not st.session_state.project_name or not st.session_state.project_id:
            st.error("Please fill in all the required fields!")
        elif not st.session_state.layers:
            st.error("Please select at least one layer.")
        elif not st.session_state.start_location or not st.session_state.end_location:
            st.error("Please fill in the start and end locations.")
        else:
            database = read_database()
            new_project = {
                "constructor": st.session_state["constructor_name"],
                "project_name": st.session_state.project_name,
                "project_id": st.session_state.project_id,
                "layers": st.session_state.layers,
                "total_distance_km": st.session_state.total_distance,
                "time_required_months": st.session_state.time_required,
                "location": f"{st.session_state.start_location} to {st.session_state.end_location}",
                "updates": [],
            }
            database.append(new_project)
            write_database(database)
            st.success(f"Project '{st.session_state.project_name}' created successfully!")
