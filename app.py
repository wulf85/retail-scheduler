import streamlit as st
import datetime
import pandas as pd
from roster import RosterGenerator, Staff, ALL_DAYS, WEEKENDS
from utils import save_staff_to_json, load_staff_from_json, parse_weekly_requests_csv
from offday_calendar import generate_offday_matrix, update_offday_request
from activities import daily_activities
from quotes import weekly_quotes

st.set_page_config(page_title="Retail Roster Planner", layout="wide")
st.title("🧭 Retail Roster Planner")

if "staff_list" not in st.session_state:
    st.session_state.staff_list = []
    st.session_state.training_schedule = {}
    st.session_state.weekly_activities = {}

# Sidebar
with st.sidebar:
    st.header("📅 Schedule Settings")
    opening = st.time_input("Opening Time", datetime.time(11, 0))
    closing = st.time_input("Closing Time", datetime.time(21, 0))
    min_weekday = st.number_input("Min Staff (Weekdays)", value=6)
    min_weekend = st.number_input("Min Staff (Weekends)", value=7)
    opt_weekday = st.number_input("Optimal Staff (Weekdays)", value=7)
    opt_weekend = st.number_input("Optimal Staff (Weekends)", value=8)
    selected_week = st.selectbox("Week", [f"Week {i+1}" for i in range(4)])

    st.markdown("## ➕ Add Staff")
    name = st.text_input("Name")
    role = st.selectbox("Role", ["Regular", "Cashier", "Supervisor"])
    availability = st.multiselect("Availability", ALL_DAYS)
    training_day = st.selectbox("Training Day", ["None"] + availability)
    train_start = st.time_input("Training Start", datetime.time(12, 0))
    train_end = st.time_input("Training End", datetime.time(17, 0))
    off_days = st.multiselect(f"{selected_week} Off-Day Requests", ALL_DAYS)

    if st.button("Add to Team") and name:
        staff = Staff(name, role, availability)
        staff.weekly_off_requests[selected_week] = off_days
        st.session_state.staff_list.append(staff)
        if training_day != "None":
            st.session_state.training_schedule.setdefault(name, {})[training_day] = (train_start, train_end)
        st.success(f"{name} added.")

    st.markdown("## ❌ Remove Staff")
    remove_name = st.selectbox("Select Staff", ["None"] + [s.name for s in st.session_state.staff_list])
    if st.button("Remove Staff") and remove_name != "None":
        st.session_state.staff_list = [s for s in st.session_state.staff_list if s.name != remove_name]
        st.session_state.training_schedule.pop(remove_name, None)
        st.success(f"{remove_name} removed.")

    st.markdown("## 💾 Save & Load")
    if st.button("Save Team"):
        save_staff_to_json(st.session_state.staff_list, st.session_state.training_schedule)
    if st.button("Load Team"):
        staff, schedule = load_staff_from_json()
        st.session_state.staff_list = staff
        st.session_state.training_schedule = schedule
        st.success("Team loaded.")

    st.markdown("## 📤 Upload Off-Day CSV")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded:
        data = parse_weekly_requests_csv(uploaded)
        count = 0
        for s in st.session_state.staff_list:
            if s.name in data:
                s.weekly_off_requests.update(data[s.name])
                count += 1
        st.success(f"Imported requests for {count} staff.")

    sample_csv = "Staff Name,Week,Requested Off Days\nAlice,Week 1,\"1, 4\"\nBob,Week 2,\"3\""
    st.download_button("📎 Download CSV Template", sample_csv.encode("utf-8"), "off_day_requests_template.csv")

    st.markdown("## ⚙️ Smart Balance Mode")
    enable_smart = st.checkbox("Enable Smart Balance Mode", value=True)
    avoid_consec_close = st.checkbox("Avoid consecutive closings", value=True)
    avoid_consec_incharge = st.checkbox("Avoid consecutive in-charges", value=True)
    max_close = st.number_input("Max Closing Shifts/Week", value=3, min_value=1)
    max_incharge = st.number_input("Max In-Charge Shifts/Week", value=3, min_value=1)

# Weekly activities
st.subheader(f"📌 Daily Activities ({selected_week})")
if selected_week not in st.session_state.weekly_activities:
    st.session_state.weekly_activities[selected_week] = daily_activities.copy()

with st.expander("Edit Activities"):
    for day in ALL_DAYS:
        activity = st.text_input(day, value=st.session_state.weekly_activities[selected_week].get(day, ""))
        st.session_state.weekly_activities[selected_week][day] = activity

st.markdown(f"### 📝 Quote of the Week\n> {weekly_quotes[int(selected_week[-1]) - 1]}")

# Calendar View
st.subheader("📅 Weekly Off-Day Overview")
matrix = generate_offday_matrix(st.session_state.staff_list, selected_week)
st.dataframe(matrix)

edit_name = st.selectbox("Staff to Edit", [s.name for s in st.session_state.staff_list])
edit_day = st.selectbox("Day to Change", ALL_DAYS)
new_status = st.selectbox("Status", ["🛌 Requested", "✅ Available"])
if st.button("Update Off-Day"):
    update_offday_request(st.session_state.staff_list, edit_name, selected_week, edit_day, new_status)
    st.success(f"{edit_day} updated for {edit_name}")

# Generate roster
if st.button("📊 Generate Roster"):
    planner = RosterGenerator(
        staff_list=st.session_state.staff_list,
        opening_hour=opening.strftime("%H:%M"),
        closing_hour=closing.strftime("%H:%M"),
        min_staff_weekday=min_weekday,
        min_staff_weekend=min_weekend,
        optimal_staff_weekday=opt_weekday,
        optimal_staff_weekend=opt_weekend,
        training_schedule=st.session_state.training_schedule,
        activities=st.session_state.weekly_activities[selected_week],
        enforce_non_consecutive_closing=avoid_consec_close,
        enforce_non_consecutive_incharge=avoid_consec_incharge,
        max_closing_per_week=max_close,
        max_incharge_per_week=max_incharge,
        auto_tune_enabled=enable_smart
    )

    st.markdown(f"🔧 **Smart Balance Mode:** {'Enabled' if enable_smart else 'Disabled'}")
    roster_df = planner.generate(week_id=selected_week)
    st.subheader("📋 Roster")
    st.dataframe(roster_df)

    st.subheader("🔍 Staff Summary")
    st.dataframe(planner.summary())

    st.subheader("🧮 Coverage Overview")
    coverage = []
    for day in ALL_DAYS:
        assigned = sum(1 for s in st.session_state.staff_list if s.schedule.get(day) and s.schedule[day] != "OFF")
        required = min_weekend if day in WEEKENDS else min_weekday
        status = "✅" if assigned >= required else "⚠️ Understaffed"
        coverage.append((day, assigned, required, status))
    st.dataframe(pd.DataFrame(coverage, columns=["Day", "Assigned", "Minimum", "Status"]))

    st.subheader("⚠️ Violations & Adjustments")
    for v in planner.list_violations():
        st.warning(v)

    if st.button("📥 Export to Excel"):
        planner.export_to_excel("weekly_roster.xlsx")
        with open("weekly_roster.xlsx", "rb") as f:
            st.download_button("Download Excel", f, "weekly_roster.xlsx")
