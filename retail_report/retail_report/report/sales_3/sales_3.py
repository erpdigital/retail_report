# Copyright (c) 2023, Alimerdan Rahimov and contributors
# For license information, please see license.txt

import frappe
from frappe import _


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
            "label": _("Total Quantity sold"),
            "fieldname": "qty",
            "fieldtype": "Float",
            "width": 120
        },


	   {
            "label": _("Price"),
            "fieldname": "avr_price",
            "fieldtype": "Float",
            "width": 120
        }
	,
        {
            "label": _("Sold Amount"),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Valuation Rate"),
            "fieldname": "valuation_rate",
            "fieldtype": "Currency",
            "width": 120
        },
	{
            "label": _("Bought amount"),
            "fieldname": "bought_amount",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Gross Profit"),
            "fieldname": "gross_profit",
            "fieldtype": "Data",
            "width": 120
        }]
	if not filters:
		filters = {}

	
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

    
	query = """
		SELECT item_code, item_name, 
		round(qty,2) as qty, 
		round(amount,2) as amount, 
		round(avr_price,2) as avr_price,
        round((sum_valuation_rate/counter_val),2) as valuation_rate, 
		round((amount-qty*(sum_valuation_rate/ counter_val)),2) as gross_profit,
		round(qty*(sum_valuation_rate/ counter_val),2) as bought_amount
FROM (
  SELECT sle.item_code as item_code, si.item_name as item_name,
         si.sum_qty as qty, si.sum_amount as amount,
         si.sum_amount/si.sum_qty as avr_price, 
         sum(sle.valuation_rate) as sum_valuation_rate,
	     count(*)  as counter_val
  FROM `tabStock Ledger Entry` as sle 
  INNER JOIN (
    SELECT Sum(qty) as sum_qty, sum(amount) as sum_amount, item_code, item_name 
    FROM `tabSales Invoice Item`
    WHERE creation BETWEEN %(from_date)s AND %(to_date)s
      AND docstatus = 1
     
    GROUP BY item_code
  ) as si ON si.item_code = sle.item_code  
  WHERE 
    sle.actual_qty<0 and
     sle.voucher_type = 'Sales Invoice' and 
   sle.docstatus =1
  GROUP BY sle.item_code
) as subquery
 
	"""
	data = frappe.db.sql(query, {"from_date": from_date,"to_date": to_date}, as_dict=True)
	return columns, data