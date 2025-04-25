# File: work_time_report.py

import frappe
from datetime import datetime, timedelta, time

def execute(filters=None):
    from_date = datetime.strptime(filters.get("from_date"), "%Y-%m-%d").date()
    to_date = datetime.strptime(filters.get("to_date"), "%Y-%m-%d").date()

    employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name", "holiday_list", "default_shift"])

    dates = []
    current = from_date
    while current <= to_date:
        dates.append(current)
        current += timedelta(days=1)

    columns = [
        {"label": "Employee ID", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150}
    ] + [{"label": d.strftime('%a %d-%m'), "fieldname": d.strftime('%Y_%m_%d'), "fieldtype": "HTML", "width": 100} for d in dates]

    data = []

    for emp in employees:
        row = {
            "employee": emp.name,
            "employee_name": emp.employee_name
        }

        for date in dates:
            status_html = get_attendance_status(emp, date)
            row[date.strftime('%Y_%m_%d')] = status_html

        data.append(row)

    return columns, data

def get_attendance_status(emp, date):
    checkin = frappe.db.get_value("Employee Checkin", {
        "employee": emp.name,
        "log_type": "IN",
        "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
    }, "time")

    checkout = frappe.db.get_value("Employee Checkin", {
        "employee": emp.name,
        "log_type": "OUT",
        "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
    }, "time")

    shift = frappe.get_doc("Shift Type", emp.default_shift) if emp.default_shift else None
    shift_start_time = None

    if shift and shift.start_time:
        if isinstance(shift.start_time, timedelta):
            # Convert timedelta to datetime.time
            total_seconds = int(shift.start_time.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            shift_start_time = time(hours, minutes, seconds)
        else:
            shift_start_time = shift.start_time  # Assuming it's already a time object

    shift_start = datetime.combine(date, shift_start_time) if shift_start_time else None

    grace = shift.late_entry_grace_period if shift else 0

    holiday = frappe.db.exists("Holiday", {"holiday_date": date, "parent": emp.holiday_list}) if emp.holiday_list else None

    on_leave = frappe.db.exists("Leave Application", {
        "employee": emp.name,
        "from_date": ["<=", date],
        "to_date": [">=", date],
        "status": "Approved",
        "docstatus": 1
