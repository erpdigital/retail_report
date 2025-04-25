import frappe
from datetime import datetime, timedelta

def execute(filters=None):
    from_date = datetime.strptime(filters.get("from_date"), "%Y-%m-%d").date()
    to_date = datetime.strptime(filters.get("to_date"), "%Y-%m-%d").date()

    employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name", "holiday_list", "default_shift"])

    # Get all dates between range
    dates = []
    current = from_date
    while current <= to_date:
        dates.append(current)
        current += timedelta(days=1)

    # Report columns
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
            row[date.strftime('%Y_%m_%d')] = get_attendance_status(emp, date)

        data.append(row)

    return columns, data


def get_attendance_status(emp, date):
    # Check-ins
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

    # Shift & grace
    shift_start = None
    grace = 0
    if emp.default_shift:
        shift = frappe.get_doc("Shift Type", emp.default_shift)
        if shift.start_time:
            shift_start = datetime.combine(date, shift.start_time)
            grace = shift.late_entry_grace_period or 0

    # Holiday check
    is_holiday = False
    if emp.holiday_list:
        is_holiday = frappe.db.exists("Holiday", {"holiday_date": date, "parent": emp.holiday_list})

    # Leave check
    is_on_leave = frappe.db.exists("Leave Application", {
        "employee": emp.name,
        "from_date": ["<=", date],
        "to_date": [">=", date],
        "status": "Approved",
        "docstatus": 1
    })

    # Logic + styling
    if is_holiday:
        return '<div style="background:#d4edda;padding:4px;border-radius:4px;text-align:center">Holiday</div>'
    elif is_on_leave:
        return '<div style="background:#fff3cd;padding:4px;border-radius:4px;text-align:center">Leave</div>'
    elif not checkin and not checkout:
        return '<div style="background:#000;color:#fff;padding:4px;border-radius:4px;text-align:center">Absent</div>'
    else:
        checkin_str = datetime.strptime(checkin, "%Y-%m-%d %H:%M:%S").strftime('%H:%M') if checkin else "-"
        checkout_str = datetime.strptime(checkout, "%Y-%m-%d %H:%M:%S").strftime('%H:%M') if checkout else "-"

        # Late check
        if checkin and shift_start:
            actual_checkin = datetime.strptime(checkin, "%Y-%m-%d %H:%M:%S")
            latest_allowed = shift_start + timedelta(minutes=grace)
            if actual_checkin > latest_allowed:
                checkin_str = f'<span style="color:red">{checkin_str}</span>'

        return f'<div style="text-align:center">{checkin_str} - {checkout_str}</div>'
