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
            "label": _("Total Quantity"),
            "fieldname": "total_qty_sold",
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
    temp.item_code as item_code, 
    temp.item_name as item_name, 
    temp.total_qty_received as total_qty_received , 
     
    temp.price AS price, 
     from  (
    SELECT 
             si.item_code as item_code, 
	    	si.item_name as item_name,
		    Sum(purchase.qty)  as total_qty_received,
            sum(si.qty) AS total_qty_sold, 
	        purchase.price as price,
            (purchase.price*SUM(si.qty))  as total_amount
        FROM (Select distinct  pi.item_code as item_code, pi.rate as price, pi.qty as qty
	             from 
		         `tabPurchase Invoice Item` as pi
            JOIN `tabPurchase Invoice` AS p ON pi.parent = p.name
            join  `tabSupplier` AS su ON p.supplier = su.name
             where 
	               su.name = %(supplier)s 
		           and p.posting_date >= %(from_date)s AND  p.posting_date <= %(to_date)s
			        and p.docstatus = 1
			group by 
			  item_code	
		     ) as purchase join 
            `tabSales Invoice Item` AS si
	    JOIN `tabSales Invoice` s ON si.parent = s.name
           
        WHERE 
	    si.item_code = purchase.item_code 
	    and 
	    si.modified >= %(from_date)s AND si.modified <= %(to_date)s
	     AND s.posting_date >= %(from_date)s AND s.posting_date <= %(to_date)s
	    AND si.docstatus = 1 AND s.docstatus = 1 
        group by
	 si.item_code, 
    si.item_name, 
    purchase.price, 
    purchase.item_code
	  UNION 
        SELECT 
            pi.item_code AS item_code, 
            pi.item_name AS item_name,
            SUM(pi.qty) AS total_qty_received,
            0 AS total_qty_sold, 
            pi.rate AS price,
            0 AS total_amount
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
    ) AS temp 
GROUP BY 
    temp.item_code
	    """
    
	data = frappe.db.sql(query, {"supplier": supplier,"from_date": from_date,"to_date": to_date}, as_dict=True)

	return columns, data