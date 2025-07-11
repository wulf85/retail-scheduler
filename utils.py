import json
import datetime
import pandas as pd
from roster import Staff
from collections import defaultdict

def save_staff_to_json(staff_list, training_schedule, filename="staff_data.json"):
    data = {
        "staff": [],
        "training_schedule": {},
        "weekly_off_requests": {}
    }

    for staff in staff_list:
        data["staff"].append({
            "name": staff.name,
            "role": staff.role,
            "availability": staff.availability,
            "max_hours": staff.max_hours,
            "min_off_days": staff.min_off_days
        })
        data["weekly_off_requests"][staff.name] = staff.weekly_off_requests

    for name, sched in training_schedule.items():
        data["training_schedule"][name] = {
            day: [t.strftime("%H:%M") for t in times]
            for day, times in sched.items()
        }

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

def load_staff_from_json(filename="staff_data.json"):
    with open(filename, "r") as f:
        data = json.load(f)

    staff_list = []
    for s in data["staff"]:
        staff = Staff(
            name=s["name"], role=s["role"],
            availability=s["availability"],
            max_hours=s["max_hours"],
            min_off_days=s["min_off_days"]
        )
        staff.weekly_off_requests = data.get("weekly_off_requests", {}).get(s["name"], {})
        staff_list.append(staff)

    training_schedule = {}
    for name, sched in data.get("training_schedule", {}).items():
        training_schedule[name] = {
            day: (
                datetime.datetime.strptime(times[0], "%H:%M").time(),
                datetime.datetime.strptime(times[1], "%H:%M").time()
            ) for day, times in sched.items()
        }

    return staff_list, training_schedule

def parse_weekly_requests_csv(uploaded_file):
    import csv
    from roster import ALL_DAYS
    decoded = uploaded_file.read().decode("utf-8").splitlines()
    reader = csv.DictReader(decoded)
    requests = defaultdict(lambda: defaultdict(list))  # staff → week → day names

    for row in reader:
        name = str(row.get("Staff Name", "")).strip()
        week = str(row.get("Week", "")).strip()
        raw = row.get("Requested Off Days", "")
        try:
            nums = [int(d.strip()) for d in raw.split(",") if d.strip().isdigit()]
            day_names = [ALL_DAYS[n - 1] for n in nums if 1 <= n <= 7]
            requests[name][week] = day_names
        except Exception:
            continue
    return requests
