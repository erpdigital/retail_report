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
            "label": _("Total Quantity Receied"),
            "fieldname": "total_qty_received",
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
            "label": _("Total "),
            "fieldname": "total",
            "fieldtype": "Float",
            "width": 120
        },
      ]
	if not filters:
		filters = {}

	supplier = filters.get("supplier")
	from_date = filters["from_date"]
	to_date = filters["to_date"]
	if not supplier:
		return [], []
    
	query = """
        SELECT 
            pi.item_code AS item_code, 
            pi.item_name AS item_name,
            SUM(pi.qty) AS total_qty_received,
            pi.rate AS price,
            SUM(pi.qty) * pi.rate as total
        FROM 
            `tabPurchase Invoice Item` AS pi 
            JOIN `tabPurchase Invoice` AS p ON pi.parent = p.name
	   
            JOIN `tabSupplier` AS su ON p.supplier = su.name
	    
        WHERE 
            su.name = %(supplier)s
            AND p.posting_date >= %(from_date)s 
            AND p.posting_date <= %(to_date)s

            AND pi.docstatus = 1 
            AND p.docstatus = 1 
        GROUP BY 
            pi.item_code

	    """
    
	data = frappe.db.sql(query, {"supplier": supplier,"from_date": from_date,"to_date": to_date}, as_dict=True)

	return columns, data