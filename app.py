import streamlit as st
import datetime
import pandas as pd
from roster import RosterGenerator, Staff, ALL_DAYS, WEEKENDS
from utils import save_staff_to_json, load_staff_from_json, parse_weekly_requests_csv
from offday_calendar import generate_offday_matrix, update_offday_request
from activities import daily_activities
from quotes import weekly_quotes

st.set_page_config(page_title="Retail Roster Scheduler", layout="wide")
st.title("🧭 Retail Roster Scheduler")

if "staff_list" not in st.session_state:
    st.session_state.staff_list = []
    st.session_state.training_schedule = {}
    st.session_state.weekly_activities = {}

# Sidebar
with st.sidebar:
    st.header("📅 Settings")
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
    remove_name = st.selectbox("Remove", ["None"] + names)
    if st.button("Remove") and remove_name != "None":
        st.session_state.staff_list = [s for s in st.session_state.staff_list if s.name != remove_name]
        st.session_state.training_schedule.pop(remove_name, None)
        st.success(f"{remove_name} removed.")

    st.markdown("## 💾 Save & Load")
    if st.button("Save Team"):
        save_staff_to_json(st.session_state.staff_list, st.session_state.training_schedule)
    if st.button("Load Team"):
        staff, sched = load_staff_from_json()
        st.session_state.staff_list = staff
        st.session_state.training_schedule = sched
        st.success("Team loaded.")

    st.markdown("## 📥 Upload Off-Day CSV")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded:
        request_data = parse_weekly_requests_csv(uploaded)
        updated_count = 0
        for s in st.session_state.staff_list:
            if s.name in request_data:
                s.weekly_off_requests.update(request_data[s.name])
                updated_count += 1
        st.success(f"Imported requests for {updated_count} staff members.")
    template_csv = "Staff Name,Week,Requested Off Days\nAlice,Week 1,\"1, 4\"\nBob,Week 2,\"3\""
    st.download_button("📎 Download CSV Template", template_csv.encode("utf-8"), "off_day_requests_template.csv")

    st.markdown("## ⚙️ Smart Balance Mode")
    smart_enabled = st.checkbox("Enable Smart Balance Mode", value=True)
    no_consec_close = st.checkbox("Avoid consecutive closings", value=True)
    no_consec_incharge = st.checkbox("Avoid consecutive in-charges", value=True)
    max_close = st.number_input("Max closing shifts/week", value=3, min_value=1)
    max_incharge = st.number_input("Max in-charge shifts/week", value=3, min_value=1)

# Weekly Activities
st.subheader(f"📌 Activities ({selected_week})")
if selected_week not in st.session_state.weekly_activities:
    st.session_state.weekly_activities[selected_week] = daily_activities.copy()
with st.expander("Edit Activities"):
    for day in ALL_DAYS:
        act = st.text_input(f"{day}", value=st.session_state.weekly_activities[selected_week].get(day, ""))
        st.session_state.weekly_activities[selected_week][day] = act

for day in ALL_DAYS:
    st.markdown(f"**{day}**: {st.session_state.weekly_activities[selected_week].get(day)}")

quote_idx = int(selected_week.split()[-1]) - 1
st.markdown(f"### 📝 Quote of the Week\n> {weekly_quotes[quote_idx]}")

# Off-Day Editor
st.subheader(f"📅 Weekly Requests: {selected_week}")
matrix = generate_offday_matrix(st.session_state.staff_list, selected_week)
st.dataframe(matrix)

edit_name = st.selectbox("Edit Staff", [s.name for s in st.session_state.staff_list])
edit_day = st.selectbox("Edit Day", ALL_DAYS)
edit_status = st.selectbox("Change to", ["🛌 Requested", "✅ Available"])
if st.button("Update Request"):
    update_offday_request(st.session_state.staff_list, edit_name, selected_week, edit_day, edit_status)
    st.success(f"{edit_day} updated for {edit_name}.")

# Generate Roster
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
        activities=st.session_state.weekly_activities[selected_week],
        enforce_non_consecutive_closing=no_consec_close,
        enforce_non_consecutive_incharge=no_consec_incharge,
        max_closing_per_week=max_close,
        max_incharge_per_week=max_incharge,
        auto_tune_enabled=smart_enabled
    )

    st.markdown(f"🔧 **Smart Balance Mode:** {'Enabled' if smart_enabled else 'Disabled'}")
    df = generator.generate(week_id=selected_week)
    st.subheader("📋 Weekly Roster")
    st.dataframe(df)

    st.subheader("🔍 Staff Summary")
    st.dataframe(generator.summary())

    st.subheader("🧮 Daily Coverage")
    coverage = []
    for day in ALL_DAYS:
        assigned = sum(1 for s in st.session_state.staff_list if s.schedule.get(day) and s.schedule[day] != "OFF")
        required = min_weekend if day in WEEKENDS else min_weekday
        status = "✅" if assigned >= required else "⚠️ Understaffed"
        coverage.append((day, assigned, required, status))
    st.dataframe(pd.DataFrame(coverage, columns=["Day", "Assigned", "Minimum", "Status"]))

    st.subheader("⚠️ Violations & Actions")
    for v in generator.list_violations():
        st.warning(v)

    if st.button("📥 Export to Excel"):
        generator.export_to_excel("weekly_roster.xlsx")
        with open("weekly_roster.xlsx", "rb") as f:
            st.download_button("Download Excel", f, file_name="weekly_roster.xlsx")
