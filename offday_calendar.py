import pandas as pd
from roster import ALL_DAYS

def generate_offday_matrix(staff_list, week_id):
    matrix = {
        "Staff": [],
        **{day: [] for day in ALL_DAYS}
    }

    for staff in staff_list:
        matrix["Staff"].append(staff.name)
        requested = staff.weekly_off_requests.get(week_id, [])
        for day in ALL_DAYS:
            if day in requested:
                matrix[day].append("🛌 Requested")
            elif day not in staff.availability:
                matrix[day].append("🚫 Unavailable")
            else:
                matrix[day].append("✅ Available")

    return pd.DataFrame(matrix)

def update_offday_request(staff_list, staff_name, week_id, day, status):
    staff = next((s for s in staff_list if s.name == staff_name), None)
    if not staff: return

    requests = staff.weekly_off_requests.get(week_id, [])
    if status == "🛌 Requested":
        if day not in requests:
            requests.append(day)
    elif status == "✅ Available":
        if day in requests:
            requests.remove(day)
    staff.weekly_off_requests[week_id] = requests
