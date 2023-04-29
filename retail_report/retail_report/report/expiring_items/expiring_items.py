from __future__ import unicode_literals
import frappe
from frappe import _
import datetime

def execute(filters=None):
    if not filters: filters = {}

    columns = get_columns()
    data = get_expiring_items(filters)

    return columns, data

def get_columns():
    return [
        _("Item Code") + ":Link/Item:100",
        _("Item Name") + "::150",
        _("Batch No") + ":Link/Batch:100",
        _("Expiry Date") + ":Date:100",
        _("Days to Expire") + ":Int:100",
        _("Warehouse") + ":Link/Warehouse:150",
        _("Stock UOM") + "::80",
        _("Quantity") + ":Float:80",
    ]

def get_expiring_items(filters):
    conditions = build_conditions(filters)
    query = """
        SELECT
            batch.item, item.item_name, batch.name, batch.expiry_date,
            DATEDIFF(batch.expiry_date, CURDATE()) as days_to_expire,
            sle.warehouse, item.stock_uom, sle.actual_qty
        FROM
            `tabBatch` batch
        JOIN
            `tabStock Ledger Entry` sle ON batch.name = sle.batch_no
        JOIN
            `tabItem` item ON item.name = batch.item
        WHERE
            batch.expiry_date IS NOT NULL
            AND sle.actual_qty > 0
            {conditions}
        ORDER BY
            batch.expiry_date ASC, batch.item ASC
    """.format(conditions=conditions)

    data = frappe.db.sql(query, as_list=True)
    return data

def build_conditions(filters):
    conditions = ""

    if filters.get("item_code"):
        conditions += " AND batch.item = '{0}'".format(frappe.db.escape(filters["item_code"]))

    if filters.get("warehouse"):
        conditions += " AND sle.warehouse = '{0}'".format(frappe.db.escape(filters["warehouse"]))

    return conditions