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
            "fieldname": "sold_amount",
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
     Select 
    i.item_code as item_code,
    i.item_name as item_name,
    case 
    when 
    (-1)*sold_items.sum < 0 then 0
    else (-1)*sold_items.sum 
    end as  total_qty_sold,
    case 
    when 
    (-1)*sold_items.sum <= 0 then 0
    When (-1)*sold_items.sum > 0 then (-1)*sold_items.sum * ip.price_list_rate 

    end as   sold_amount,
    ip.price_list_rate as price
From 
   `tabItem` as i 
    Join `tabBin` as bin on i.item_code = bin.item_code
    JOIN `tabItem Supplier` as si ON si.parent = i.item_code
    join `tabItem Price` as ip on i.item_code = ip.item_code and 	ip.price_list = 'Standard Buying' 
    and 
    (ip.valid_from >= %(from_date)s or ip.valid_from is NULL) and 
    (ip.valid_upto <= %(to_date)s or ip.valid_upto is NULL)
    
    Left join
(SELECT 
    i.item_code,
    i.item_name,
    Sum(sle.actual_qty) as sum
	FROM 
    `tabItem` as i 
    JOIN `tabItem Supplier` as si ON si.parent = i.item_code
    LEFT JOIN `tabStock Ledger Entry` as sle ON sle.item_code = i.item_code AND 
     sle.is_cancelled = 0 AND sle.voucher_type LIKE 'Sales Invoice' 
WHERE
   
    si.supplier = %(supplier)s and 
    sle.posting_date  >= %(from_date)s and  sle.posting_date   
    group by 
    i.item_code) as sold_items on sold_items.item_code = i.item_code     
	where 
	si.supplier = %(supplier)s

    group by 
    i.item_code
    Order by total_qty_sold desc
	    """
    
	data = frappe.db.sql(query, {"supplier": supplier,"from_date": from_date,"to_date": to_date}, as_dict=True)

	return columns, data