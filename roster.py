# roster.py
import datetime
from typing import List
import pandas as pd
from collections import defaultdict

ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKENDS = ["Saturday", "Sunday"]

class Staff:
    def __init__(self, name, role, availability, max_hours=44, min_off_days=2):
        self.name = name
        self.role = role
        self.availability = availability
        self.max_hours = max_hours
        self.min_off_days = min_off_days
        self.weekly_off_requests = {}  # e.g. { "Week 1": ["Monday", "Thursday"] }
        self.schedule = {}             # e.g. { "Monday": (start_time, end_time) or None }
        self.total_hours = 0

    def assign_shift(self, day, start, end):
        duration = datetime.datetime.combine(datetime.date.today(), end) - datetime.datetime.combine(datetime.date.today(), start)
        hours = duration.total_seconds() / 3600
        self.schedule[day] = (start, end)
        self.total_hours += hours

    def is_available(self, day):
        return day in self.availability and self.schedule.get(day) is None


class RosterGenerator:
    def __init__(self, staff_list: List[Staff], opening_hour="11:00", closing_hour="21:00",
                 report_lead=30, handover_extension=60,
                 min_staff_weekday=6, min_staff_weekend=7,
                 optimal_staff_weekday=7, optimal_staff_weekend=8,
                 training_schedule=None, activities=None):
        self.staff_list = staff_list
        self.opening_time = datetime.datetime.strptime(opening_hour, "%H:%M").time()
        self.closing_time = datetime.datetime.strptime(closing_hour, "%H:%M").time()
        self.report_time = self._subtract_minutes(self.opening_time, report_lead)
        self.handover_time = self._add_minutes(self.closing_time, handover_extension)
        self.min_weekday = min_staff_weekday
        self.min_weekend = min_staff_weekend
        self.opt_weekday = optimal_staff_weekday
        self.opt_weekend = optimal_staff_weekend
        self.training_schedule = training_schedule or {}
        self.activities = activities or {}
        self.roster = pd.DataFrame(index=[s.name for s in staff_list], columns=ALL_DAYS)
        self.violations = []

    def _subtract_minutes(self, time_obj, minutes):
        return (datetime.datetime.combine(datetime.date.today(), time_obj) - datetime.timedelta(minutes=minutes)).time()

    def _add_minutes(self, time_obj, minutes):
        return (datetime.datetime.combine(datetime.date.today(), time_obj) + datetime.timedelta(minutes=minutes)).time()

    def assign_off_days(self, week_id):
        for staff in self.staff_list:
            current_offs = set(day for day in ALL_DAYS if staff.schedule.get(day) is None)
            requested = staff.weekly_off_requests.get(week_id, [])
            scheduled = set(staff.schedule.keys())
            needed = staff.min_off_days - len(current_offs)

            selected = [d for d in requested if d in staff.availability and d not in scheduled][:needed]
            remaining = staff.min_off_days - len(selected)

            fillable = [d for d in staff.availability if d not in scheduled and d not in selected]
            selected += fillable[:remaining]

            for day in selected:
                staff.schedule[day] = None
                self.roster.at[staff.name, day] = "OFF"

    def assign_daily_in_charge(self):
        pool = [s for s in self.staff_list if len(s.availability) >= 5]
        count_tracker = defaultdict(int)
        for day in ALL_DAYS:
            eligible = [s for s in pool if s.is_available(day)]
            if not eligible:
                self.violations.append(f"No in-charge available for {day}")
                continue
            selected = sorted(eligible, key=lambda s: count_tracker[s.name])[0]
            selected.assign_shift(day, datetime.time(10, 0), datetime.time(22, 0))
            self.roster.at[selected.name, day] = "In-Charge: 10:00–22:00"
            count_tracker[selected.name] += 1

    def assign_closing_staff(self):
        count_tracker = defaultdict(int)
        for day in ALL_DAYS:
            eligible = [s for s in self.staff_list if s.is_available(day)]
            sorted_pool = sorted(eligible, key=lambda s: count_tracker[s.name])
            assigned = False
            for staff in sorted_pool:
                staff.assign_shift(day, self.report_time, datetime.time(22, 0))
                self.roster.at[staff.name, day] = f"Closing: {self.report_time.strftime('%H:%M')}–22:00"
                count_tracker[staff.name] += 1
                assigned = True
                break
            if not assigned:
                self.violations.append(f"No closing staff available on {day}")

    def generate(self, week_id="Week 1"):
        self.assign_off_days(week_id)
        self.assign_daily_in_charge()
        self.assign_closing_staff()

        day_counts = defaultdict(int)

        for day in ALL_DAYS:
            available = [s for s in self.staff_list if s.is_available(day)]
            preferred = [s for s in available if day in s.weekly_off_requests.get(week_id, [])]
            working_pool = [s for s in available if s not in preferred]
            cap = self.opt_weekend if day in WEEKENDS else self.opt_weekday

            for staff in working_pool[:cap]:
                if day in staff.schedule: continue
                if staff.name in self.training_schedule and day in self.training_schedule[staff.name]:
                    start, end = self.training_schedule[staff.name][day]
                    staff.assign_shift(day, start, end)
                    self.roster.at[staff.name, day] = f"Training: {start.strftime('%H:%M')}–{end.strftime('%H:%M')}"
                else:
                    staff.assign_shift(day, self.report_time, self.closing_time)
                    self.roster.at[staff.name, day] = f"{self.report_time.strftime('%H:%M')}–{self.closing_time.strftime('%H:%M')}"
                day_counts[day] += 1

            # Ensure minimum staffing
            required = self.min_weekend if day in WEEKENDS else self.min_weekday
            if day_counts[day] < required:
                extra_pool = [s for s in available if day not in s.schedule]
                for s in extra_pool[:required - day_counts[day]]:
                    s.assign_shift(day, self.report_time, self.closing_time)
                    self.roster.at[s.name, day] = f"{self.report_time.strftime('%H:%M')}–{self.closing_time.strftime('%H:%M')}"
                    day_counts[day] += 1

        for staff in self.staff_list:
            off_count = sum(1 for v in staff.schedule.values() if v is None)
            if off_count < staff.min_off_days:
                self.violations.append(f"{staff.name} has only {off_count} off-days.")
            if staff.total_hours > staff.max_hours:
                self.violations.append(f"{staff.name} exceeds max hours: {staff.total_hours:.1f}")

        for day in ALL_DAYS:
            min_req = self.min_weekend if day in WEEKENDS else self.min_weekday
            if day_counts[day] < min_req:
                self.violations.append(f"{day} has only {day_counts[day]} staff (min required: {min_req})")

        return self.roster

    def summary(self):
        return pd.DataFrame({
            "Staff": [s.name for s in self.staff_list],
            "Total Hours": [round(s.total_hours, 2) for s in self.staff_list],
            "Days Scheduled": [len([d for d, v in s.schedule.items() if v]) for s in self.staff_list],
            "Off-Days": [len([d for d, v in s.schedule.items() if v is None]) for s in self.staff_list]
        })

    def list_violations(self):
        return self.violations

    def export_to_excel(self, filename="weekly_roster.xlsx"):
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill

        wb = Workbook()
        ws = wb.active
        ws.title = "Roster"

        # Insert daily activity header
        activity_row = ["Activity"] + [self.activities.get(day, "—") for day in ALL_DAYS]
        ws.append(activity_row)

        # Insert schedule grid
        ws.append(["Staff"] + ALL_DAYS)
        for staff in self.staff_list:
            row = [staff.name]
            for day in ALL_DAYS:
                row.append(self.roster.at[staff.name, day] or "")
            ws.append(row)

        # Color code cells
        for row in ws.iter_rows(min_row=3, min_col=2):
            for cell in row:
                value = cell.value or ""
                if "In-Charge" in value:
                    cell.fill = PatternFill(start_color="FFA500", fill_type="solid")  # Orange
                elif "Closing" in value:
                    cell.fill = PatternFill(start_color="87CEEB", fill_type="solid")  # Blue
                elif "Training" in value:
                    cell.fill = PatternFill(start_color="90EE90", fill_type="solid")                 
                elif "Training" in value:
                    cell.fill = PatternFill(start_color="90EE90", fill_type="solid")  # Green
                elif value == "OFF":
                    cell.fill = PatternFill(start_color="D3D3D3", fill_type="solid")  # Gray

        wb.save(filename)
