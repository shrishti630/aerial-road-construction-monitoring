import json
import os
from datetime import datetime

DB_PATH = "data/database2.json"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)  # Ensure the database directory exists

def read_database():
    """Read the JSON database and return a list of projects."""
    try:
        if not os.path.exists(DB_PATH):
            # Initialize an empty database if the file doesn't exist
            print(f"Database not found. Initializing a new database at {DB_PATH}.")
            write_database([])
            return []

        with open(DB_PATH, "r") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, ValueError):
        # Handle empty or corrupt JSON file by reinitializing
        print(f"Database corrupted. Reinitializing at {DB_PATH}.")
        write_database([])
        return []

def write_database(data):
    """Write to the JSON database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)  # Ensure the directory exists
    with open(DB_PATH, "w") as file:
        json.dump(data, file, indent=4)

def validate_update(update):
    """
    Validate the update structure to ensure all required fields are present.

    Parameters:
    - update: The update dictionary to validate.

    Returns:
    - None if valid; raises ValueError if invalid.
    """
    required_keys = [
        "date", "layer", "confidence", "distance_covered", 
        "start_coordinates", "end_coordinates"
    ]
    missing_keys = [key for key in required_keys if key not in update]
    if missing_keys:
        raise ValueError(f"Missing required keys in update: {', '.join(missing_keys)}")

def assign_batch_number(updates, new_update):
    """
    Assign a batch number to the new update based on its layer occurrences.

    Parameters:
    - updates: List of existing updates for the project.
    - new_update: The new update to be added.

    Returns:
    - The batch number for the new update.
    """
    layer = new_update["layer"]

    # Filter updates for the same layer and sort by date and timestamp
    layer_updates = [
        update for update in updates if update["layer"] == layer
    ]
    layer_updates.sort(key=lambda x: (x["date"], x.get("timestamp", "")))

    # The batch number is the count of previous occurrences of this layer + 1
    return len(layer_updates) + 1

def add_project_update(project_id, update):
    """
    Add a new update to a specific project with batch number assignment.

    Expected `update` keys:
    - "date": str (YYYY-MM-DD)
    - "layer": str (Predicted layer)
    - "confidence": str (e.g., "85.67%")
    - "distance_covered": float (meters)
    - "start_coordinates": tuple (latitude, longitude)
    - "end_coordinates": tuple (latitude, longitude)
    - (Optional) "timestamp": str (e.g., "12:34:56" for time of update)
    """
    validate_update(update)  # Ensure all required fields are present

    # Add a default timestamp if missing
    update["timestamp"] = update.get("timestamp", datetime.now().strftime("%H:%M:%S"))

    database = read_database()

    # Find the project in the database
    for project in database:
        if project["project_id"] == project_id:
            updates = project.setdefault("updates", [])

            # Assign batch number dynamically based on the new logic
            update["batch_number"] = assign_batch_number(updates, update)

            # Check for duplicates
            if update in updates:
                raise ValueError("Duplicate update detected. Update not added.")

            # Add the update
            updates.append(update)
            break
    else:
        raise ValueError(f"Project with ID '{project_id}' not found.")

    # Save the updated database
    write_database(database)
