import streamlit as st
import datetime
import pandas as pd
from roster import RosterGenerator, Staff, ALL_DAYS
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

# Sidebar inputs
with st.sidebar:
    st.header("📅 Schedule Settings")
    opening_time = st.time_input("Opening Time", value=datetime.time(11, 0))
    closing_time = st.time_input("Closing Time", value=datetime.time(21, 0))
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
    training_start = st.time_input("Training Start", value=datetime.time(12, 0))
    training_end = st.time_input("Training End", value=datetime.time(17, 0))
    off_days_week = st.multiselect(f"{selected_week} Off-Day Requests", ALL_DAYS)

    if st.button("Add to Team") and name:
        staff = Staff(name, role, availability)
        staff.weekly_off_requests[selected_week] = off_days_week
        st.session_state.staff_list.append(staff)
        if training_day != "None":
            if name not in st.session_state.training_schedule:
                st.session_state.training_schedule[name] = {}
            st.session_state.training_schedule[name][training_day] = (training_start, training_end)
        st.success(f"{name} added.")

    st.markdown("## ❌ Remove Staff")
    names = [s.name for s in st.session_state.staff_list]
    remove_name = st.selectbox("Select", ["None"] + names)
    if st.button("Remove") and remove_name != "None":
        st.session_state.staff_list = [s for s in st.session_state.staff_list if s.name != remove_name]
        st.session_state.training_schedule.pop(remove_name, None)
        st.success(f"{remove_name} removed.")

    st.markdown("## 💾 Save/Load")
    if st.button("Save"):
        save_staff_to_json(st.session_state.staff_list, st.session_state.training_schedule)
    if st.button("Load"):
        staff, sched = load_staff_from_json()
        st.session_state.staff_list = staff
        st.session_state.training_schedule = sched
        st.success("Team loaded.")

    st.markdown("## 📤 Upload Off-Day CSV")
    uploaded_csv = st.file_uploader("Upload CSV File", type=["csv"])
    if uploaded_csv:
        requests = parse_weekly_requests_csv(uploaded_csv)
        count = 0
        for s in st.session_state.staff_list:
            if s.name in requests:
                s.weekly_off_requests.update(requests[s.name])
                count += 1
        st.success(f"Imported requests for {count} staff.")

    template = "Staff Name,Week,Requested Off Days\nAlice,Week 1,\"1, 4\"\nBob,Week 2,\"3\"\nCharlie,Week 2,\"2, 5, 7\""
    st.download_button("📎 Download CSV Template", template.encode("utf-8"), "off_day_requests_template.csv")

# Daily Activities
st.subheader(f"📌 Daily Activities ({selected_week})")
if selected_week not in st.session_state.weekly_activities:
    st.session_state.weekly_activities[selected_week] = daily_activities.copy()

with st.expander("🛠️ Edit Activities"):
    for day in ALL_DAYS:
        act = st.text_input(f"{day}:", value=st.session_state.weekly_activities[selected_week].get(day, ""))
        st.session_state.weekly_activities[selected_week][day] = act

for day in ALL_DAYS:
    st.markdown(f"**{day}:** {st.session_state.weekly_activities[selected_week].get(day, '—')}")

# Quote
quote_index = int(selected_week.split()[-1]) - 1
st.markdown(f"## 📝 Quote of the Week\n> {weekly_quotes[quote_index]}")

# Off-day Calendar
st.subheader(f"📅 Off-Day Requests for {selected_week}")
calendar_df = generate_offday_matrix(st.session_state.staff_list, selected_week)
st.dataframe(calendar_df)

st.markdown("### ✏️ Modify Individual Request")
edit_name = st.selectbox("Select Staff", [s.name for s in st.session_state.staff_list])
edit_day = st.selectbox("Select Day", ALL_DAYS)
new_status = st.selectbox("Status", ["🛌 Requested", "✅ Available"])
if st.button("Update Off-Day"):
    update_offday_request(st.session_state.staff_list, edit_name, selected_week, edit_day, new_status)
    st.success(f"{edit_day} updated for {edit_name}")

# Generate roster
if st.button("📊 Generate Roster"):
    generator = RosterGenerator(
        staff_list=st.session_state.staff_list,
        opening_hour=opening_time.strftime("%H:%M"),
        closing_hour=closing_time.strftime("%H:%M"),
        min_staff_weekday=min_weekday,
        min_staff_weekend=min_weekend,
        optimal_staff_weekday=opt_weekday,
        optimal_staff_weekend=opt_weekend,
        training_schedule=st.session_state.training_schedule,
        activities=st.session_state.weekly_activities[selected_week]
    )

    roster_df = generator.generate(week_id=selected_week)
    st.subheader("📋 Weekly Roster")
    st.dataframe(roster_df)

    st.subheader("🔍 Staff Summary")
    st.dataframe(generator.summary())

    # Coverage overview
    st.subheader("🧮 Daily Coverage Overview")
    coverage = []
    for day in ALL_DAYS:
        assigned = sum(
            1 for s in st.session_state.staff_list if s.schedule.get(day) and s.schedule.get(day) != "OFF"
        )
        required = min_weekend if day in ["Saturday", "Sunday"] else min_weekday
        status = "✅" if assigned >= required else "⚠️ Understaffed"
        coverage.append((day, assigned, required, status))
    st.dataframe(pd.DataFrame(coverage, columns=["Day", "Assigned", "Minimum", "Status"]))

    st.subheader("⚠️ Violations")
    for v in generator.list_violations():
        st.warning(v)

    if st.button("📤 Export to Excel"):
        generator.export_to_excel("weekly_roster.xlsx")
        with open("weekly_roster.xlsx", "rb") as f:
            st.download_button("Download Excel", f, file_name="weekly_roster.xlsx")
