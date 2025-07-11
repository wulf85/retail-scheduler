import streamlit as st
from roster import RosterGenerator, Staff, ALL_DAYS
import datetime

st.title("Retail Roster Scheduler")

# --- Staff Setup ---
if "staff_list" not in st.session_state:
    st.session_state.staff_list = []

st.subheader("Staff Registration")

name = st.text_input("Name")
role = st.selectbox("Role", ["Crew", "Supervisor"])
availability = st.multiselect("Available Days", ALL_DAYS)
add_btn = st.button("Add Staff")

if add_btn and name and availability:
    st.session_state.staff_list.append(
        Staff(name, role, availability, max_hours=9999, min_off_days=2)
    )

for s in st.session_state.staff_list:
    st.markdown(f"- {s.name} ({s.role}): Available on {', '.join(s.availability)}")

# --- Roster Settings ---
st.subheader("Roster Rules")

opening = st.time_input("Opening Time", datetime.time(11, 0))
closing = st.time_input("Closing Time", datetime.time(21, 0))
min_weekday = st.slider("Minimum Weekday Staff", 1, 10, 6)
min_weekend = st.slider("Minimum Weekend Staff", 1, 10, 6)

avoid_consec_close = st.checkbox("Avoid Consecutive Closings", value=True)
avoid_consec_incharge = st.checkbox("Avoid Consecutive In-Charge", value=True)
max_close = st.slider("Max Closings per Week", 0, 7, 5)
max_incharge = st.slider("Max In-Charge per Week", 0, 7, 3)
enable_smart = st.checkbox("Enable Smart Auto-Tuning", value=True)

# --- Generate Button ---
if st.button("Generate Roster"):
    planner = RosterGenerator(
        staff_list=st.session_state.staff_list,
        opening_hour=opening.strftime("%H:%M"),
        closing_hour=closing.strftime("%H:%M"),
        min_staff_weekday=min_weekday,
        min_staff_weekend=min_weekend,
        training_schedule={},  # Add logic here later if needed
        activities={},         # Optional: inject from external inputs
        enforce_non_consecutive_closing=avoid_consec_close,
        enforce_non_consecutive_incharge=avoid_consec_incharge,
        max_closing_per_week=max_close,
        max_incharge_per_week=max_incharge,
        auto_tune_enabled=enable_smart
    )

    roster = planner.generate()
    st.subheader("Weekly Roster")
    st.dataframe(roster.fillna(""), use_container_width=True)

    st.subheader("Summary")
    st.dataframe(planner.summary())

    st.subheader("Violations & Auto-Fixes")
    for v in planner.list_violations():
        st.markdown(f"• {v}")

    if st.button("Export to Excel"):
        planner.export_to_excel("weekly_roster.xlsx")
        st.success("Roster exported to weekly_roster.xlsx")
