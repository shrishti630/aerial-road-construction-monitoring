import streamlit as st

# Set page configuration for a centered layout
st.set_page_config(page_title="Road Construction Monitoring", page_icon="🛠️", layout="wide")

# Import necessary modules
from utils.authentication import render_engineer_login, render_constructor_login, authenticate_user
from utils.ui_helpers import apply_global_styles
import pages.dashboard_constructor as constructor_page
import pages.dashboard_engineer as engineer_page
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


import base64

#your logo image
def add_logo_to_sidebar(logo_path, width=120):
    with open(logo_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()

    st.sidebar.markdown(
        f"""
        <style>
        /* Push default sidebar nav down */
        section[data-testid="stSidebar"] > div:first-child {{
            padding-top: 20px;
        }}
        /* Insert logo at top fixed */
        .sidebar-logo {{
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 1000;
        }}
        </style>
        <div class="sidebar-logo">
            <img src="data:image/png;base64,{encoded}" width="{width}">
        </div>
        """,
        unsafe_allow_html=True
    )


st.set_page_config(layout="wide")
add_logo_to_sidebar("./assets/logo.png")  

def set_background_from_base64(image_path):
    with open(image_path, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/png;base64,{b64_string}");
                background-size: cover;
                background-repeat: no-repeat;
                background-attachment: fixed;
                background-position: center;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

# ✅ Call the function with your full local file path (no file:///)
set_background_from_base64("./assets/bg1.png")


# Apply global styles
apply_global_styles()

# Hide the sidebar
# st.markdown(
#     """
#     <style>
#     [data-testid="stSidebar"] {
#         display: none;
#     }
#     .stApp {
#         max-width: 1000px; /* Centered layout width */
#         margin: auto;
#     }
#         /* Hide the scrollbar */
#     ::-webkit-scrollbar {
#         width: 0px;
#         height: 0px;
#     }
#     ::-webkit-scrollbar-thumb {
#         background: transparent;
#     }
#     ::-webkit-scrollbar-track {
#         background: transparent;
#     }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

def main():
    # Initialize session state variables for authentication and modal state
    if "Engineer_authenticated" not in st.session_state:
        st.session_state["Engineer_authenticated"] = False

    if "Constructor_authenticated" not in st.session_state:
        st.session_state["Constructor_authenticated"] = False

    if "current_form" not in st.session_state:
        st.session_state["current_form"] = None  # Track which login form is active: 'Engineer' or 'Constructor'

    # Redirect to dashboards if authenticated
    if st.session_state["Engineer_authenticated"]:
        import pages.dashboard_engineer as engineer_page
        engineer_page.render()
    elif st.session_state["Constructor_authenticated"]:
        import pages.dashboard_constructor as constructor_page
        constructor_page.render()
    else:
        render_home()

def local_gif_to_html(gif_path):
        with open(gif_path, "rb") as f:
            data_url = base64.b64encode(f.read()).decode("utf-8")
        return f"""
        <div style="text-align: center;">
            <img src="data:image/gif;base64,{data_url}" alt="gif" width="200">
        </div>
        """

def render_home():
    # Center the title with custom CSS
    st.markdown(
        """
        <style>
        .title-container {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            margin-top: 10px;
            border: 2px solid black;
            box-shadow:10px 5px 5px red,-1em 0 0.4em olive;;
            padding: 30px ;    
        }
        .title-text {
            font-size: 45px;
            font-weight: bold;
            text-align: center;
            color: black;;
        }
        .subtitle {
            font-size: 20px;
            font-weight: bold;
            text-align: center;
            color: black;
        }
        </style>
        <div class="title-container">
            <div class="title-text">
                🚧 Road Construction Monitoring
            </div>
            <p class="subtitle">Simplifying Construction Oversight with Intelligence <br>Providing innovative solutions that enhance efficiency, streamline processes, and foster seamless collaboration.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # ✅ Use the actual GIF file path here
    gif_html = local_gif_to_html("./assets/GIF1.gif")

    # ✅ Render it
    st.markdown(gif_html, unsafe_allow_html=True)

    st.markdown(
        """
        <div style="text-align: center; margin-top: 0px; margin-bottom: 20px; color: black;">
            <h2>Select Your Role</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Two columns for horizontal buttons
    col1, col2 = st.columns(2)

    with col1:
        engineer_clicked = st.button("🧑‍🏭 Engineer", use_container_width=True)

    with col2:
        constructor_clicked = st.button("👷 Constructor", use_container_width=True)

    # Set session state based on button click
    if engineer_clicked:
        st.session_state["current_form"] = "Engineer"
    elif constructor_clicked:
        st.session_state["current_form"] = "Constructor"

    # Render the active login form based on `current_form`
    if st.session_state["current_form"] == "Engineer":
        render_engineer_login_form()
    elif st.session_state["current_form"] == "Constructor":
        render_constructor_login_form()

def render_engineer_login_form():
    """Display the Engineer login form."""
    st.subheader("Engineer Login")
    username = st.text_input("Username", key="engineer_username")
    password = st.text_input("Password", type="password", key="engineer_password")

    if st.button("Login"):
        if authenticate_user("Engineer", username, password):
            st.success("Logged in successfully as Engineer!")
            st.session_state["Engineer_authenticated"] = True
            st.session_state["current_form"] = None  # Clear the active form
            st.session_state["refresh_trigger"] = not st.session_state.get("refresh_trigger", False)
        else:
            st.error("Invalid username or password.")

def render_constructor_login_form():
    """Display the Constructor login form."""
    st.subheader("Constructor Login")
    username = st.text_input("Username", key="constructor_username")
    password = st.text_input("Password", type="password", key="constructor_password")

    if st.button("Login"):
        if authenticate_user("Constructor", username, password):
            st.success("Logged in successfully as Constructor!")
            st.session_state["Constructor_authenticated"] = True
            st.session_state["Constructor_authenticated_user"] = username  # Save username for filtering projects
            st.session_state["current_form"] = None  # Clear the active form
            st.session_state["refresh_trigger"] = not st.session_state.get("refresh_trigger", False)
        else:
            st.error("Invalid username or password.")

if __name__ == "__main__":
    main()

# Run the main function to start the app