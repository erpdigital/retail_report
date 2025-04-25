# File: weekly_attendance_overview.py

import frappe
from datetime import datetime, timedelta

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
    shift_start = datetime.combine(date, shift.start_time) if shift and shift.start_time else None
    grace = shift.late_entry_grace_period if shift else 0

    holiday = frappe.db.exists("Holiday", {"holiday_date": date, "parent": emp.holiday_list}) if emp.holiday_list else None

    on_leave = frappe.db.exists("Leave Application", {
        "employee": emp.name,
        "from_date": ["<=", date],
        "to_date": [">=", date],
        "status": "Approved",
        "docstatus": 1
    })

    if holiday:
        return f'<div style="background:#d4edda;padding:4px;border-radius:4px;text-align:center">Holiday</div>'
    elif on_leave:
        return f'<div style="background:#fff3cd;padding:4px;border-radius:4px;text-align:center">Leave</div>'
    elif not checkin and not checkout:
        return f'<div style="background:#000;color:#fff;padding:4px;border-radius:4px;text-align:center">Absent</div>'
    else:
        checkin_str = datetime.strptime(checkin, "%Y-%m-%d %H:%M:%S").strftime('%H:%M') if checkin else "-"
        checkout_str = datetime.strptime(checkout, "%Y-%m-%d %H:%M:%S").strftime('%H:%M') if checkout else "-"

        if shift_start and checkin:
            shift_grace = shift_start + timedelta(minutes=grace)
            checkin_dt = datetime.strptime(checkin, "%Y-%m-%d %H:%M:%S")
            if checkin_dt > shift_grace:
                checkin_str = f'<span style="color:red">{checkin_str}</span>'

        return f'<div style="text-align:center">{checkin_str} - {checkout_str}</div>'
