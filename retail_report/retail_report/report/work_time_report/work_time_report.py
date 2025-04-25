import frappe
from datetime import datetime, timedelta

def get_attendance_status(emp, date):
    # Check if the employee has a holiday or leave
    on_leave = frappe.db.exists("Leave Application", {
        "employee": emp,
        "from_date": ["<=", date],
        "to_date": [">=", date],
        "status": "Approved"
    })

    on_holiday = frappe.db.exists("Holiday", {
        "holiday_date": date
    })

    # Get the shift information
    shift = frappe.get_all("Shift", filters={"employee": emp}, fields=["start_time", "end_time"])

    # Default status
    status = "Absent"  # Default status is absent

    if on_leave:
        status = "Leave"
    elif on_holiday:
        status = "Holiday"
    elif shift:
        shift_start = datetime.combine(date, shift[0].start_time) if shift[0].start_time else None
        shift_end = datetime.combine(date, shift[0].end_time) if shift[0].end_time else None
        attendance = frappe.get_all("Attendance", filters={
            "employee": emp,
            "attendance_date": date
        })

        if attendance:
            checkin_time = datetime.strptime(attendance[0].checkin, "%Y-%m-%d %H:%M:%S") if attendance[0].checkin else None
            if checkin_time:
                # If check-in time is later than the shift start time, it's late
                if checkin_time > shift_start:
                    status = "Late"
                else:
                    status = "On Time"
            else:
                status = "Absent"
        else:
            status = "Absent"

    return status, shift_start, shift_end


def execute(filters):
    employees = frappe.get_all("Employee", fields=["name", "employee_name", "department", "designation"])
    results = []

    worked_days = 0
    absent_days = 0
    late_days = 0

    for emp in employees:
        row = {
            "employee_name": emp.employee_name,
            "employee_id": emp.name,
            "worked_days": 0,
            "absent_days": 0,
            "late_days": 0,
            "attendance": []
        }

        for date in filters["date_range"]:
            status, shift_start, shift_end = get_attendance_status(emp.name, date)

            row["attendance"].append(status)

            if status == "On Time" or status == "Late":
                row["worked_days"] += 1
                worked_days += 1

            if status == "Absent":
                row["absent_days"] += 1
                absent_days += 1

            if status == "Late":
                row["late_days"] += 1
                late_days += 1

        # Append the worked_days, absent_days, and late_days for each employee
        results.append(row)

    # Add the total summary row with worked, absent, and late days
    summary_row = {
        "employee_name": "Total",
        "worked_days": worked_days,
        "absent_days": absent_days,
        "late_days": late_days,
        "attendance": []
    }

    results.append(summary_row)

    # Returning the results with the added summary columns
    return results
