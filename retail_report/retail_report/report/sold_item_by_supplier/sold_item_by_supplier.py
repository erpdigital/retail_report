# Copyright (c) 2023, Alimerdan Rahimov and contributors
# For license information, please see license.txt

import frappe

from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = [
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 120
        },
	 {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Link",
            "options": "Item",
            "width": 120
        },
        {
            "label": _("Total Quantity"),
            "fieldname": "total_qty",
            "fieldtype": "Float",
            "width": 120
        },
	   {
            "label": _("Price"),
            "fieldname": "price",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": _("Total Amount"),
            "fieldname": "total_amount",
            "fieldtype": "Currency",
            "width": 120
        }]
	if not filters:
		filters = {}

	supplier = filters.get("supplier")
	from_date = filters["from_date"]
	to_date = filters["to_date"]
	if not supplier:
		return [], []

	query = """
        SELECT 
            si.item_code, 
	    	si.item_name,
            SUM(si.qty) AS total_qty, 
	        pi.price_list_rate as price,
            (pi.price_list_rate*SUM(si.qty))  as total_amount
        FROM 
            `tabSales Invoice Item` AS si
	    JOIN `tabSales Invoice` s ON si.parent = s.name
            JOIN `tabItem` AS i ON si.item_code = i.item_code
            JOIN `tabPurchase Invoice Item` AS pi ON i.item_code = pi.item_code
            JOIN `tabPurchase Invoice` AS p ON pi.parent = p.name
            JOIN `tabSupplier` AS su ON p.supplier = su.name
        WHERE 
            su.name = %(supplier)s
	    AND si.modified BETWEEN %(from_date)s AND %(to_date)s
	     AND s.posting_date BETWEEN %(from_date)s AND %(to_date)s
	    AND si.docstatus = 1 AND s.docstatus = 1 
        GROUP BY 
            si.item_code, pi.price_list_rate
    """
    
	data = frappe.db.sql(query, {"supplier": supplier,"from_date": from_date,"to_date": to_date}, as_dict=True)

	return columns, data