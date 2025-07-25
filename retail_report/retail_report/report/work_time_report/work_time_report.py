from frappe import _  # Add this import to make __() available
import frappe
from datetime import datetime, timedelta, time
from frappe.utils import now_datetime


def execute(filters=None):
    from_date = datetime.strptime(filters.get("from_date"), "%Y-%m-%d").date()
    to_date = datetime.strptime(filters.get("to_date"), "%Y-%m-%d").date()

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "holiday_list", "default_shift"]
    )

    dates = []
    current = from_date
    while current <= to_date:
        dates.append(current)
        current += timedelta(days=1)

    columns = [
    {"label": _("ID сотрудника"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
    {"label": _("Имя сотрудника"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150}
] + [
    {"label": d.strftime('%a %d-%m'), "fieldname": d.strftime('%Y_%m_%d'), "fieldtype": "HTML", "width": 100}
    for d in dates
] + [
    {"label": _("Всего праздников"), "fieldname": "total_holidays", "fieldtype": "Int", "width": 120},
    {"label": _("Всего отпусков"), "fieldname": "total_leaves", "fieldtype": "Int", "width": 120},
    {"label": _("Всего отсутствий"), "fieldname": "total_absences", "fieldtype": "Int", "width": 120},
    {"label": _("Количество дней с опозданием"), "fieldname": "total_late_entry_days", "fieldtype": "Int", "width": 160},
    {"label": _("Общее количество минут опоздания"), "fieldname": "total_late_entry_minutes", "fieldtype": "Int", "width": 160},
    {"label": _("Общее количество рабочих дней"), "fieldname": "total_workdays", "fieldtype": "Int", "width": 120}
]

    data = []
    for emp in employees:
        row = {"employee": emp.name, "employee_name": emp.employee_name}
        total_holidays = 0
        total_leaves = 0
        total_absences = 0
        total_late_entry_days = 0
        total_late_entry_minutes = 0
        total_workdays = 0  # Initialize total workdays

        for date in dates:
            status, late_entry_minutes = get_attendance_status(emp, date)
            row[date.strftime('%Y_%m_%d')] = status
            if 'Holiday' in status:
                total_holidays += 1
            elif 'Leave' in status:
                total_leaves += 1
            elif 'Absent' in status:
                total_absences += 1
            if late_entry_minutes > 0:
                total_late_entry_days += 1
                total_late_entry_minutes += late_entry_minutes
            if 'Holiday' not in status and 'Leave' not in status and 'Absent' not in status:
                total_workdays += 1  # Count workdays

        row["total_holidays"] = total_holidays
        row["total_leaves"] = total_leaves
        row["total_absences"] = total_absences
        row["total_late_entry_days"] = total_late_entry_days
        row["total_late_entry_minutes"] = total_late_entry_minutes
        row["total_workdays"] = total_workdays  # Add total workdays to row
        data.append(row)

    return columns, data


def get_attendance_status(emp, date):
    # Fetch check-in and check-out
    checkin_time = frappe.db.sql(""" 
        SELECT time FROM `tabEmployee Checkin`
        WHERE employee = %s AND log_type = 'IN' AND time BETWEEN %s AND %s
        ORDER BY time ASC LIMIT 1
    """, (emp.name, f"{date} 00:00:00", f"{date} 23:59:59"), as_dict=1)

    # Get last check-out
    checkout_time = frappe.db.sql(""" 
        SELECT time FROM `tabEmployee Checkin`
        WHERE employee = %s AND log_type = 'OUT' AND time BETWEEN %s AND %s
        ORDER BY time DESC LIMIT 1
    """, (emp.name, f"{date} 00:00:00", f"{date} 23:59:59"), as_dict=1)

    checkin = checkin_time[0]["time"] if checkin_time else None
    checkout = checkout_time[0]["time"] if checkout_time else None

    # Shift start and grace
    shift_start_time = None
    grace = 0
    if emp.default_shift:
        shift = frappe.get_doc("Shift Type", emp.default_shift)
        if shift.start_time:
            if isinstance(shift.start_time, timedelta):
                secs = int(shift.start_time.total_seconds())
                h, m = divmod(secs, 3600)
                m, s = divmod(m, 60)
                shift_start_time = time(h, m, s)
            else:
                shift_start_time = shift.start_time
            grace = shift.late_entry_grace_period or 0

    shift_start = datetime.combine(date, shift_start_time) if shift_start_time else None

    # Holiday and leave checks
    is_holiday = emp.holiday_list and frappe.db.exists(
        "Holiday", {"holiday_date": date, "parent": emp.holiday_list}
    )
    is_on_leave = frappe.db.exists("Leave Application", {
        "employee": emp.name,
        "from_date": ["<=", date],
        "to_date": [">=", date],
        "status": "Approved",
        "docstatus": 1
    })

    late_entry_minutes = 0

    # 1. If there's any checkin or checkout, show attendance ignoring holiday
    if checkin or checkout:
        # Format times
        checkin_str = checkin.strftime('%H:%M') if isinstance(checkin, datetime) else '-'
        checkout_str = checkout.strftime('%H:%M') if isinstance(checkout, datetime) else '-'
        # Late check-in
        if shift_start and checkin:
            checkin_dt = checkin if isinstance(checkin, datetime) else datetime.strptime(checkin, "%Y-%m-%d %H:%M:%S")
            if checkin_dt > shift_start + timedelta(minutes=grace):
                checkin_str = f'<span style="color:red">{checkin_str}</span>'
                late_entry_minutes = (checkin_dt - shift_start - timedelta(minutes=grace)).seconds // 60
                if late_entry_minutes < 0:
                    late_entry_minutes = 0
        return f'<div style="text-align:center">{checkin_str} - {checkout_str}</div>', late_entry_minutes

    # 2. Holiday (no checkin) -> green
    if is_holiday:
        return f'<div style="background:#d4edda;padding:4px;border-radius:4px;text-align:center">{_("Holiday")}</div>', late_entry_minutes

    # 3. Approved leave -> yellow
    if is_on_leave:
        return f'<div style="background:#fff3cd;padding:4px;border-radius:4px;text-align:center">{_("Leave")}</div>', late_entry_minutes

    # 4. If it's today and shift hasn't started yet, leave empty
    now = now_datetime()
    if date == now.date() and shift_start and now < shift_start:
        return f'<div style="text-align:center">-</div>', late_entry_minutes

    # 5. Absent -> black
    return f'<div style="background:#000;color:#fff;padding:4px;border-radius:4px;text-align:center">{_("Absent")}</div>', late_entry_minutes
