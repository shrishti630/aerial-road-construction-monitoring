import matplotlib.pyplot as plt
import datetime
import streamlit as st

def render_header(title, icon="📋"):
    st.markdown(f"<h2 style='text-align: center;'>{icon} {title}</h2>", unsafe_allow_html=True)

def plot_distance_coverage(updates):
    dates = [datetime.datetime.strptime(update["date"], "%Y-%m-%d") for update in updates]
    distances = [update["distance_covered"] for update in updates]
    fig, ax = plt.subplots()
    ax.plot(dates, distances, marker="o", linestyle="-")
    ax.set_xlabel("Date")
    ax.set_ylabel("Distance Covered (meters)")
    ax.set_title("Distance Coverage Over Time")
    st.pyplot(fig)

def work_speed_trend(updates):
    dates = [datetime.datetime.strptime(update["date"], "%Y-%m-%d") for update in updates]
    distances = [update["distance_covered"] for update in updates]
    daily_speeds = []
    for i in range(1, len(distances)):
        time_diff = (dates[i] - dates[i - 1]).days
        distance_diff = distances[i] - distances[i - 1]
        daily_speed = distance_diff / time_diff if time_diff > 0 else 0
        daily_speeds.append(daily_speed)
    fig, ax = plt.subplots()
    ax.plot(dates[1:], daily_speeds, marker="o", linestyle="-")
    ax.set_xlabel("Date")
    ax.set_ylabel("Work Speed (meters/day)")
    ax.set_title("Work Speed Trend")
    st.pyplot(fig)

# Apply global styles and set the layout to wide
def apply_global_styles():
    # Add custom styles
    st.markdown(
        """
        <style>
        div.streamlit-expander {
            max-width: 100%; /* Full width */
            margin: auto;    /* Center the content */
        }

        section.main {
            max-width: 1600px; /* Adjust to your desired width */
            margin: auto;
        }

        /* Optional: Add styling for scrollbars or other elements */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-thumb {
            background: #888; 
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #555; 
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
