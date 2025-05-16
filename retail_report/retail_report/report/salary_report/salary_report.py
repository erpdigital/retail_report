import frappe
from datetime import datetime, timedelta
from frappe.utils import get_first_day, get_last_day, now_datetime

def execute(filters=None):
    from_date = datetime.strptime(filters.get("from_date"), "%Y-%m-%d").date()
    to_date = datetime.strptime(filters.get("to_date"), "%Y-%m-%d").date()

    employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name", "holiday_list", "daily_wage"])

    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Worked Days", "fieldname": "worked_days", "fieldtype": "Int", "width": 120},
        {"label": "Absent Days", "fieldname": "absent_days", "fieldtype": "Int", "width": 120},
        {"label": "Leave Days", "fieldname": "leave_days", "fieldtype": "Int", "width": 120},
        {"label": "Holiday Days", "fieldname": "holidays", "fieldtype": "Int", "width": 120},
        {"label": "Bonus", "fieldname": "bonus", "fieldtype": "Currency", "width": 100},
        {"label": "Daily Wage", "fieldname": "daily_wage", "fieldtype": "Currency", "width": 100},
        {"label": "Calculated Salary", "fieldname": "calculated_salary", "fieldtype": "Currency", "width": 150}
    ]

    data = []
    for emp in employees:
        worked_days = absent_days = leave_days = holidays = 0
        bonus = 0
        daily_wage = emp.daily_wage or 0

        current = from_date
        while current <= to_date:
            status = get_or_create_attendance(emp, current)
            if status == "Present":
                worked_days += 1
            elif status == "Absent":
                absent_days += 1
            elif status == "On Leave":
                leave_days += 1
            elif status == "Holiday":
                holidays += 1
            current += timedelta(days=1)

        salary = worked_days * daily_wage + bonus
        data.append({
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "worked_days": worked_days,
            "absent_days": absent_days,
            "leave_days": leave_days,
            "holidays": holidays,
            "bonus": bonus,
            "daily_wage": daily_wage,
            "calculated_salary": salary
        })

    return columns, data


def get_or_create_attendance(emp, date):
    # First, check if attendance exists already
    existing = frappe.db.get_value("Attendance", {
        "employee": emp.name,
        "attendance_date": date
    }, "status")
    if existing:
        return existing

    # Check if it’s a holiday
    is_holiday = frappe.db.exists("Holiday", {
        "holiday_date": date,
        "parent": emp.holiday_list
    })
    if is_holiday:
        return "Holiday"

    # Check if approved leave
    is_on_leave = frappe.db.exists("Leave Application", {
        "employee": emp.name,
        "from_date": ["<=", date],
        "to_date": [">=", date],
        "status": "Approved",
        "docstatus": 1
    })
    if is_on_leave:
        return "On Leave"

    # Check Checkins
    checkin = frappe.db.exists("Employee Checkin", {
        "employee": emp.name,
        "log_type": "IN",
        "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
    })
    checkout = frappe.db.exists("Employee Checkin", {
        "employee": emp.name,
        "log_type": "OUT",
        "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
    })

    if checkin or checkout:
        status = "Present"
    else:
        status = "Absent"

    # Create attendance if needed
    attendance = frappe.new_doc("Attendance")
    attendance.employee = emp.name
    attendance.attendance_date = date
    attendance.status = status
    attendance.docstatus = 1
    attendance.save(ignore_permissions=True)

    return status
