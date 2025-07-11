import streamlit as st
from roster import RosterGenerator, Staff, ALL_DAYS
import datetime

st.set_page_config(page_title="Retail Roster Scheduler", layout="wide")
st.title("Retail Roster Scheduler")

# --- Staff Setup ---
if "staff_list" not in st.session_state:
    st.session_state.staff_list = []

st.subheader("🧑‍🤝‍🧑 Staff Registration")
with st.form("staff_form"):
    name = st.text_input("Name")
    role = st.selectbox("Role", ["Crew", "Supervisor"])
    availability = st.multiselect("Available Days", ALL_DAYS)
    submitted = st.form_submit_button("Add Staff")
    if submitted and name and availability:
        st.session_state.staff_list.append(
            Staff(name, role, availability, max_hours=9999, min_off_days=2)
        )

st.markdown("### 👥 Registered Team")
for staff in st.session_state.staff_list:
    st.write(f"- {staff.name} ({staff.role}) – Available on: {', '.join(staff.availability)}")

# --- Rules ---
st.subheader("⚙️ Scheduling Rules")
opening = st.time_input("Store Opening", datetime.time(11, 0))
closing = st.time_input("Store Closing", datetime.time(21, 0))
min_weekday = st.slider("Minimum Staff (Weekdays)", 1, 10, 6)
min_weekend = st.slider("Minimum Staff (Weekends)", 1, 10, 6)

avoid_consec_close = st.checkbox("Avoid Consecutive Closing Shifts", value=True)
avoid_consec_incharge = st.checkbox("Avoid Consecutive In-Charge Shifts", value=True)
max_close = st.slider("Max Closings per Week", 0, 7, 5)
max_incharge = st.slider("Max In-Charge per Week", 0, 7, 3)
enable_smart = st.checkbox("Enable Auto-Tuning", value=True)

# --- Generate Roster ---
if st.button("🛠️ Generate Weekly Roster") and st.session_state.staff_list:
    planner = RosterGenerator(
        staff_list=st.session_state.staff_list,
        opening_hour=opening.strftime("%H:%M"),
        closing_hour=closing.strftime("%H:%M"),
        min_staff_weekday=min_weekday,
        min_staff_weekend=min_weekend,
        training_schedule={},
        activities={},
        enforce_non_consecutive_closing=avoid_consec_close,
        enforce_non_consecutive_incharge=avoid_consec_incharge,
        max_closing_per_week=max_close,
        max_incharge_per_week=max_incharge,
        auto_tune_enabled=enable_smart
    )

    roster = planner.generate()
    st.subheader("📅 Weekly Roster")
    st.dataframe(roster.fillna(""), use_container_width=True)

    st.subheader("📊 Summary")
    st.dataframe(planner.summary())

    st.subheader("⚠️ Violations")
    for issue in planner.list_violations():
        st.markdown(f"- {issue}")

    if st.button("📤 Export Roster to Excel"):
        planner.export_to_excel("weekly_roster.xlsx")
        st.success("✅ Roster saved as weekly_roster.xlsx")
