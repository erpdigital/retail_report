import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data

def get_columns():
    return [
        {
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 150
        },
        {
            "label": _("Stock Quantity"),
            "fieldname": "stock_qty",
            "fieldtype": "Float",
            "width": 150
        },
        {
            "label": _("Stock Value"),
            "fieldname": "stock_value",
            "fieldtype": "Currency",
            "width": 150
        }
    ]

def get_data(filters):
    data = []

    datewise_stock_entries = frappe.db.sql("""
        SELECT posting_date, SUM(actual_qty) as stock_qty, SUM(stock_value) as stock_value
        FROM `tabStock Ledger Entry`
        GROUP BY posting_date
        ORDER BY posting_date
    """, as_dict=True)

    for entry in datewise_stock_entries:
        data.append({
            "date": entry.posting_date,
            "stock_qty": entry.stock_qty,
            "stock_value": entry.stock_value
        })

    return data