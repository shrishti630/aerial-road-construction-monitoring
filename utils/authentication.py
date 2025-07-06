import streamlit as st

# Default credentials for authentication
DEFAULT_CREDENTIALS = {
    "Engineer": {"username": "engineer", "password": "password123"},
    "Constructor": {"username": "constructor", "password": "password123"},
}

def authenticate_user(role, username, password):
    """Authenticate user login with default credentials."""
    default_user = DEFAULT_CREDENTIALS.get(role)
    if default_user and username == default_user["username"] and password == default_user["password"]:
        return True
    return False

def render_engineer_login():
    """Render Engineer Login Page."""
    st.title("Engineer Login")
    username = st.text_input("Username", key="engineer_username")
    password = st.text_input("Password", type="password", key="engineer_password")

    if st.button("Login"):
        if authenticate_user("Engineer", username, password):
            st.success("Logged in successfully as Engineer!")
            # Set session state for engineer login
            st.session_state["Engineer_authenticated"] = True
            st.session_state["user_role"] = "Engineer"
            st.session_state["refresh_trigger"] = not st.session_state.get("refresh_trigger", False)
        else:
            st.error("Invalid username or password.")

def render_constructor_login():
    """Render Constructor Login Page."""
    st.title("Constructor Login")
    username = st.text_input("Username", key="constructor_username")
    password = st.text_input("Password", type="password", key="constructor_password")

    if st.button("Login"):
        if authenticate_user("Constructor", username, password):
            st.success("Logged in successfully as Constructor!")
            st.session_state["Constructor_authenticated"] = True
            st.session_state["Constructor_authenticated_user"] = username  # Store the username in session
        else:
            st.error("Invalid username or password.")


def render_logout_button():
    """Render a logout button to clear session state."""
    if st.button("Logout"):
        # Clear all session states on logout
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_rerun()
