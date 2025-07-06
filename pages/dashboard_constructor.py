import streamlit as st
from utils.data_handler import read_database, write_database, add_project_update
from utils.ui_helpers import apply_global_styles
import os
from predict import predict_category
from haversine import haversine
import cv2
import datetime
import shutil

# Apply global styles for the application
apply_global_styles()

def render():
    if not st.session_state.get("Constructor_authenticated"):
        st.warning("You must log in as Constructor to access this page.")
        return

    st.title("Constructor Dashboard")

    # Logout Button
    if st.button("Logout"):
        st.session_state["Constructor_authenticated"] = False
        st.session_state["Constructor_authenticated_user"] = None
        st.session_state["user_role"] = None
        st.session_state["refresh_trigger"] = not st.session_state.get("refresh_trigger", False)

    # Navigation Options
    nav_options = ["Add Project Updates"]
    selected_option = st.selectbox("Select an Option", nav_options, key="constructor_nav")

    if selected_option == "Add Project Updates":
        view_existing_projects()


def view_existing_projects():
    st.subheader("View Existing Projects")
    database = read_database()

    if not database:
        st.info("No projects found. Start by creating a new project.")
        return

    search_query = st.text_input("Search Projects by Name or ID:", key="constructor_search_query").strip().lower()
    filtered_projects = [
        project for project in database
        if search_query in project["project_name"].lower() or search_query in project["project_id"].lower()
    ] if search_query else database

    if not filtered_projects:
        st.warning("No projects match your search query.")
        return

    for project in filtered_projects:
        expander_key = f"expander_{project['project_id']}"
        if expander_key not in st.session_state:
            st.session_state[expander_key] = False

        with st.expander(f"Project: {project['project_name']} (ID: {project['project_id']})", expanded=st.session_state[expander_key]):
            st.write(f"**Constructor**: {project['constructor']}")
            st.write(f"**Layers**: {', '.join(project['layers'])}")
            st.write(f"**Total Distance**: {project['total_distance_km']} km")
            st.write(f"**Time Required**: {project['time_required_months']} months")
            st.write(f"**Location**: {project['location']}")

            st.write("### Upload Video and SRT File")
            uploaded_video = st.file_uploader("Upload Video File", type=["mp4", "avi", "mkv"], key=f"video_{project['project_id']}")
            uploaded_srt = st.file_uploader("Upload SRT File", type=["srt"], key=f"srt_{project['project_id']}")

            if uploaded_video and uploaded_srt:
                if st.button(f"Process and Add Update to {project['project_name']}", key=f"process_{project['project_id']}"):
                    process_project_update(project, uploaded_video, uploaded_srt)


def process_project_update(project, video_file, srt_file):
    # Save files locally
    video_path = save_uploaded_file(video_file, "temp_video.mp4")
    srt_path = save_uploaded_file(srt_file, "temp_metadata.srt")

    # Initialize frame_path to None
    frame_path = None

    try:
        # Parse SRT file for GPS coordinates and calculate distance
        start_coords, end_coords = extract_coordinates_from_srt(srt_path)
        if not start_coords or not end_coords:
            st.error("Failed to extract GPS coordinates from the SRT file.")
            return

        # Extract frame from video
        batch_number = len(project.get("updates", [])) + 1  # Determine batch number dynamically
        frame_path = extract_frame_from_video(video_path, batch_number)

        # Predict the layer from the extracted frame
        if frame_path:
            success, prediction = predict_category(frame_path)
            if success:
                predicted_layer = prediction['Predicted Layer']
                confidence = prediction['Confidence']

                # Validate sequential coordinates and repetition for the same layer
                validation_error = validate_coordinates(project, start_coords, end_coords, predicted_layer)
                if validation_error:
                    st.error(validation_error)
                    return

                # Dynamically rename the extracted frame with batch number and layer
                layer_frame_path = save_frame_with_dynamic_name(frame_path, batch_number, predicted_layer)

                st.success(f"Predicted Layer: {predicted_layer} (Confidence: {confidence})")

                # Save the update in the database
                new_update = {
                    "date": str(datetime.date.today()),
                    "batch_number": batch_number,
                    "layer": predicted_layer,
                    "confidence": confidence,
                    "distance_covered": calculate_distance(start_coords, end_coords),
                    "start_coordinates": start_coords,
                    "end_coordinates": end_coords,
                    "frame_path": layer_frame_path,  # Save renamed frame path
                }
                add_project_update(project["project_id"], new_update)
                st.success("Project update added successfully!")
            else:
                st.error(prediction.get("error", "Prediction failed."))
        else:
            st.error("Failed to extract a frame from the video.")

    except Exception as e:
        st.error(f"An error occurred: {e}")

    finally:
        # Clean up temporary files
        cleanup_temp_files([video_path, srt_path, frame_path] if frame_path else [video_path, srt_path])




### Utility Functions
def validate_coordinates(project, start_coords, end_coords, layer_name, tolerance=50):
    """
    Validate GPS coordinates for sequential updates and check for repetition within the same layer.

    Parameters:
    - project: Current project data.
    - start_coords: Start coordinates of the new update.
    - end_coords: End coordinates of the new update.
    - layer_name: The name of the layer being updated.
    - tolerance: Maximum allowed distance deviation in meters.

    Returns:
    - None if validation passes; error message if validation fails.
    """
    updates = project.get("updates", [])

    # Filter updates for the same layer
    layer_updates = [update for update in updates if update["layer"] == layer_name]

    # Sequential validation
    if layer_updates:
        last_update = layer_updates[-1]  # Last update for the same layer
        prev_end = last_update["end_coordinates"]
        distance = haversine(prev_end, start_coords) * 1000  # Convert to meters

        if distance > tolerance:
            return f"Sequential validation failed: Start coordinates ({start_coords}) are too far from the previous batch's end coordinates ({prev_end})."

    # Check for repetition in the same layer
    for update in layer_updates:
        if start_coords == update["start_coordinates"] and end_coords == update["end_coordinates"]:
            return f"Repetition detected: The start and end coordinates ({start_coords}, {end_coords}) match a previous update for the same layer."

    return None




def save_uploaded_file(uploaded_file, filename):
    """Save the uploaded file to a temporary directory."""
    file_path = os.path.join("uploads", filename)
    os.makedirs("uploads", exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())
    return file_path


def extract_frame_from_video(video_path, batch_number):
    """Extract a representative frame from the video and save it temporarily."""
    try:
        cap = cv2.VideoCapture(video_path)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        mid_frame = frame_count // 2

        cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
        ret, frame = cap.read()

        if ret:
            temp_frame_path = os.path.join("uploads", f"temp_frame_batch{batch_number}.jpg")
            os.makedirs("uploads", exist_ok=True)
            cv2.imwrite(temp_frame_path, frame)
            cap.release()
            return temp_frame_path
        cap.release()
    except Exception as e:
        print(f"Error extracting frame: {e}")
    return None


def save_frame_with_dynamic_name(frame_path, batch_number, layer_name):
    """
    Save the extracted frame with a dynamic name based on batch number and layer name.

    Parameters:
    - frame_path: Original path of the extracted frame.
    - batch_number: Current batch number.
    - layer_name: Predicted layer name.

    Returns:
    - New file path for the renamed frame.
    """
    os.makedirs("assets/uploaded_images", exist_ok=True)  # Ensure the directory exists
    new_frame_name = f"batch{batch_number}_{layer_name.replace(' ', '_')}.jpg"
    new_frame_path = os.path.join("assets/uploaded_images", new_frame_name)

    shutil.move(frame_path, new_frame_path)
    return new_frame_path


def extract_coordinates_from_srt(srt_path):
    """Extract the first and last GPS coordinates from the SRT file."""
    try:
        with open(srt_path, "r") as file:
            lines = file.readlines()

        start_line = next((line for line in lines if "latitude" in line and "longitude" in line), None)
        end_line = next((line for line in reversed(lines) if "latitude" in line and "longitude" in line), None)

        if start_line and end_line:
            start_coords = extract_lat_lon(start_line)
            end_coords = extract_lat_lon(end_line)
            return start_coords, end_coords
    except Exception as e:
        print(f"Error parsing SRT file: {e}")
    return None, None



def extract_lat_lon(srt_line):
    """Extract latitude and longitude from a line of SRT content."""
    try:
        if "[latitude:" not in srt_line or "[longitude:" not in srt_line:
            raise ValueError("SRT line does not contain valid GPS coordinates.")
        
        lat_start = srt_line.find("[latitude:") + 10
        lat_end = srt_line.find("]", lat_start)
        lon_start = srt_line.find("[longitude:") + 11
        lon_end = srt_line.find("]", lon_start)

        latitude = float(srt_line[lat_start:lat_end])
        longitude = float(srt_line[lon_start:lon_end])
        return (latitude, longitude)
    except Exception as e:
        print(f"Error extracting lat/lon from SRT line: {e}")
        return None


def calculate_distance(coords1, coords2):
    """Calculate the distance between two GPS coordinates using the Haversine formula."""
    if not coords1 or not coords2:
        raise ValueError("Invalid coordinates provided for distance calculation.")
    
    return haversine(coords1, coords2) * 1000  # Convert to meters


def cleanup_temp_files(file_paths):
    """Remove temporary files."""
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted temporary file: {file_path}")
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
