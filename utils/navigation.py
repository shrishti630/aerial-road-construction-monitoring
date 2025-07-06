import streamlit as st

def navigate_to(page_name):
    """Navigate to a specific page."""
    st.session_state["current_page"] = page_name
    st.experimental_rerun()

def get_current_page():
    """Get the current page from the session state."""
    return st.session_state.get("current_page", "Home")
