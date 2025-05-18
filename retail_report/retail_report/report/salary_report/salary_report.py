import frappe
from datetime import datetime, timedelta
from frappe import _

def link_checkins_to_existing_attendance(from_date, to_date):
    # Get all attendance records between from_date and to_date
    attendance_records = frappe.get_all("Attendance", filters={
        "attendance_date": ["between", [from_date, to_date]],
        "docstatus": 1
    }, fields=["name", "employee", "attendance_date"])

    for att in attendance_records:
        date_str = att.attendance_date.strftime("%Y-%m-%d")
        checkins = frappe.get_all("Employee Checkin", filters={
            "employee": att.employee,
            "time": ["between", [f"{date_str} 00:00:00", f"{date_str} 23:59:59"]],
            "attendance": ["is", "not set"]
        }, fields=["name"])

        for chk in checkins:
            frappe.db.set_value("Employee Checkin", chk.name, "attendance", att.name)

    frappe.db.commit()
    
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
    {"label": _("Calculated Salary"), "fieldname": "calculated_salary", "fieldtype": "Currency", "width": 150},
     {"label": _("Deposit"), "fieldname": "deposit", "fieldtype": "Currency", "width": 100},
    {"label": _("Advance Payment"), "fieldname": "advance_payment", "fieldtype": "Currency", "width": 120},
    {"label": _("Total Paid"), "fieldname": "total_paid", "fieldtype": "Currency", "width": 120}    
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
            existing_row.total_paid = salary - existing_row.deposit - existing_row.advance_payment 
            bonus = existing_row.bonus
            deposit = existing_row.deposit
            advance_payment =existing_row.advance_payment
            total_paid = existing_row.total_paid
        else:
            # Create new row
            deposit = 0
            advance_payment =0
            bonus = 0
            total_paid = salary
            emp_doc.append("monthly_payroll_summary", {
        "month": month,
        "year": year,
        "worked_days": worked_days,
        "absent_days": absent_days,
        "leave_days": leave_days,
        "holidays": holidays,
        "bonus": bonus,
        "daily_wage": daily_wage,
        "calculated_salary": salary,
        "total_paid": salary      
    })
         
        emp_doc.save(ignore_permissions=True)
         
        data.append({
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "worked_days": worked_days,
            "absent_days": absent_days,
            "leave_days": leave_days,
            "holidays": holidays,
            "bonus": bonus,
            "daily_wage": daily_wage,
            "calculated_salary": salary,
            "deposit":  deposit,
            "advance_payment":  advance_payment,
            "total_paid": total_paid
        })
    link_checkins_to_existing_attendance(from_date, to_date)
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
