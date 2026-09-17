import os
import sys
import base64
import streamlit as st

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Set page configuration for a centered layout (must be the first Streamlit command)
st.set_page_config(page_title="Road Construction Monitoring", page_icon="🛠️", layout="wide")

# Import necessary modules
from utils.authentication import render_engineer_login, render_constructor_login, authenticate_user
from utils.ui_helpers import apply_global_styles
import pages.dashboard_constructor as constructor_page
import pages.dashboard_engineer as engineer_page

# Logo image helper
def add_logo_to_sidebar(logo_path, width=120):
    if not os.path.exists(logo_path):
        return
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

logo_file = os.path.join(BASE_DIR, "assets", "logo.png")
add_logo_to_sidebar(logo_file)

def set_background_from_base64(image_path):
    if not os.path.exists(image_path):
        return
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

bg_file = os.path.join(BASE_DIR, "assets", "bg1.png")
set_background_from_base64(bg_file)

# Apply global styles
apply_global_styles()

def local_gif_to_html(gif_path):
    if not os.path.exists(gif_path):
        return ""
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
        .title-container {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            margin-top: 10px;
            border: 2px solid black;
            box-shadow: 10px 5px 5px red, -1em 0 0.4em olive;
            padding: 30px;
            background-color: rgba(255, 255, 255, 0.85);
            border-radius: 8px;
        }}
        .title-text {{
            font-size: 42px;
            font-weight: bold;
            text-align: center;
            color: black;
        }}
        .subtitle {{
            font-size: 18px;
            font-weight: 500;
            text-align: center;
            color: #333;
        }}
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

    gif_file = os.path.join(BASE_DIR, "assets", "GIF1.gif")
    gif_html = local_gif_to_html(gif_file)
    if gif_html:
        st.markdown(gif_html, unsafe_allow_html=True)

    st.markdown(
        """
        <div style="text-align: center; margin-top: 15px; margin-bottom: 20px; color: black;">
            <h2>Select Your Role</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Two columns for horizontal buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🧑‍🏭 Engineer", use_container_width=True, key="role_engineer_btn"):
            st.session_state["current_form"] = "Engineer"

    with col2:
        if st.button("👷 Constructor", use_container_width=True, key="role_constructor_btn"):
            st.session_state["current_form"] = "Constructor"

    # Render the active login form based on current_form
    if st.session_state.get("current_form") == "Engineer":
        render_engineer_login_form()
    elif st.session_state.get("current_form") == "Constructor":
        render_constructor_login_form()

def render_engineer_login_form():
    """Display the Engineer login form."""
    st.markdown("---")
    st.subheader("🧑‍🏭 Engineer Login")
    username = st.text_input("Username", key="engineer_username")
    password = st.text_input("Password", type="password", key="engineer_password")

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Login", key="engineer_submit_btn"):
            if authenticate_user("Engineer", username, password):
                st.success("Logged in successfully as Engineer!")
                st.session_state["Engineer_authenticated"] = True
                st.session_state["user_role"] = "Engineer"
                st.session_state["current_form"] = None
                st.rerun()
            else:
                st.error("Invalid username or password.")
    with c2:
        if st.button("Cancel", key="engineer_cancel_btn"):
            st.session_state["current_form"] = None
            st.rerun()

def render_constructor_login_form():
    """Display the Constructor login form."""
    st.markdown("---")
    st.subheader("👷 Constructor Login")
    username = st.text_input("Username", key="constructor_username")
    password = st.text_input("Password", type="password", key="constructor_password")

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Login", key="constructor_submit_btn"):
            if authenticate_user("Constructor", username, password):
                st.success("Logged in successfully as Constructor!")
                st.session_state["Constructor_authenticated"] = True
                st.session_state["user_role"] = "Constructor"
                st.session_state["Constructor_authenticated_user"] = username
                st.session_state["current_form"] = None
                st.rerun()
            else:
                st.error("Invalid username or password.")
    with c2:
        if st.button("Cancel", key="constructor_cancel_btn"):
            st.session_state["current_form"] = None
            st.rerun()

def main():
    # Initialize session state variables
    if "Engineer_authenticated" not in st.session_state:
        st.session_state["Engineer_authenticated"] = False

    if "Constructor_authenticated" not in st.session_state:
        st.session_state["Constructor_authenticated"] = False

    if "current_form" not in st.session_state:
        st.session_state["current_form"] = None

    # Redirect to dashboards if authenticated
    if st.session_state.get("Engineer_authenticated"):
        engineer_page.render()
    elif st.session_state.get("Constructor_authenticated"):
        constructor_page.render()
    else:
        render_home()

if __name__ == "__main__":
    main()