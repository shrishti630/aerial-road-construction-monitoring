import datetime
import matplotlib.pyplot as plt
import streamlit as st

def render_header(title, icon="📋"):
    st.markdown(f"<h2 style='text-align: center;'>{icon} {title}</h2>", unsafe_allow_html=True)

def plot_distance_coverage(updates):
    if not updates:
        st.info("No update data available to plot.")
        return
    dates = [datetime.datetime.strptime(update["date"], "%Y-%m-%d") for update in updates if "date" in update]
    distances = [update["distance_covered"] for update in updates if "distance_covered" in update]
    if not dates or not distances:
        return
    fig, ax = plt.subplots()
    ax.plot(dates, distances, marker="o", linestyle="-")
    ax.set_xlabel("Date")
    ax.set_ylabel("Distance Covered (meters)")
    ax.set_title("Distance Coverage Over Time")
    fig.autofmt_xdate()
    st.pyplot(fig)
    plt.close(fig)

def work_speed_trend(updates):
    if not updates or len(updates) < 2:
        st.info("Need at least 2 updates to calculate work speed trend.")
        return
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
    fig.autofmt_xdate()
    st.pyplot(fig)
    plt.close(fig)

def apply_global_styles():
    st.markdown(
        """
        <style>
        div.streamlit-expander {
            max-width: 100%;
            margin: auto;
        }

        section.main {
            max-width: 1600px;
            margin: auto;
        }

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
