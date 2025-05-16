import frappe
from datetime import datetime, timedelta
from frappe import _
def execute(filters=None):
    from_date = datetime.strptime(filters.get("from_date"), "%Y-%m-%d").date()
    to_date = datetime.strptime(filters.get("to_date"), "%Y-%m-%d").date()

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "holiday_list", "daily_wage"]
    )

    columns = [
    {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
    {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
    {"label": _("Worked Days"), "fieldname": "worked_days", "fieldtype": "Int", "width": 120},
    {"label": _("Absent Days"), "fieldname": "absent_days", "fieldtype": "Int", "width": 120},
    {"label": _("Leave Days"), "fieldname": "leave_days", "fieldtype": "Int", "width": 120},
    {"label": _("Holiday Days"), "fieldname": "holidays", "fieldtype": "Int", "width": 120},
    {"label": _("Bonus"), "fieldname": "bonus", "fieldtype": "Currency", "width": 100},
    {"label": _("Daily Wage"), "fieldname": "daily_wage", "fieldtype": "Currency", "width": 100},
    {"label": _("Calculated Salary"), "fieldname": "calculated_salary", "fieldtype": "Currency", "width": 150}
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

        # Save to child table of Employee if entry for month/year doesn't exist
        month = from_date.strftime("%B")
        year = from_date.year
        emp_doc = frappe.get_doc("Employee", emp.name)
        existing_row = None
        for row in emp_doc.monthly_payroll_summary:
            if row.month == month and row.year == year:
                existing_row = row
                break

        if existing_row:
        # Overwrite values
            existing_row.worked_days = worked_days
            existing_row.absent_days = absent_days
            existing_row.leave_days = leave_days
            existing_row.holidays = holidays
            existing_row.daily_wage = daily_wage
            existing_row.calculated_salary = salary
        else:
            # Create new row
            emp_doc.append("monthly_payroll_summary", {
        "month": month,
        "year": year,
        "worked_days": worked_days,
        "absent_days": absent_days,
        "leave_days": leave_days,
        "holidays": holidays,
        "bonus": bonus,
        "daily_wage": daily_wage,
        "calculated_salary": salary
    })

        emp_doc.save(ignore_permissions=True)

        data.append({
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "worked_days": worked_days,
            "absent_days": absent_days,
            "leave_days": leave_days,
            "holidays": holidays,
            "bonus": existing_row.bonus,
            "daily_wage": daily_wage,
            "calculated_salary": salary
        })

    return columns, data


def get_or_create_attendance(emp, date):
    # Check if attendance already exists
    existing = frappe.db.get_value("Attendance", {
        "employee": emp.name,
        "attendance_date": date
    }, "status")
    if existing:
        return existing

    # Check for holiday
    is_holiday = frappe.db.exists("Holiday", {
        "holiday_date": date,
        "parent": emp.holiday_list
    })
    if is_holiday:
        return "Holiday"

    # Check for approved leave
    is_on_leave = frappe.db.exists("Leave Application", {
        "employee": emp.name,
        "from_date": ["<=", date],
        "to_date": [">=", date],
        "status": "Approved",
        "docstatus": 1
    })
    if is_on_leave:
        return "On Leave"

    # Check for checkins
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

    # Create attendance
    attendance = frappe.new_doc("Attendance")
    attendance.employee = emp.name
    attendance.attendance_date = date
    attendance.status = status
    attendance.docstatus = 1
    attendance.save(ignore_permissions=True)

    return status
