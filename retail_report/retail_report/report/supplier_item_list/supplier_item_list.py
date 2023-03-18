# Copyright (c) 2023, Alimerdan Rahimov and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions
from frappe import _
from frappe.utils import flt
from frappe.query_builder.functions import CombineDatetime
from erpnext.stock.doctype.warehouse.warehouse import apply_warehouse_filter
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
            "fieldname": "Total_qty",
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
        }
	,
        {
            "label": _("Total Amount"),
            "fieldname": "total_amount",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Sold Amount"),
            "fieldname": "sold_amount",
            "fieldtype": "Currency",
            "width": 120
        }]
	if not filters:
		filters = {}

	supplier = filters.get("supplier")
	from_date = filters["from_date"]
	to_date = filters["to_date"]
	sle = get_stock_ledger_entries(filters, [])
	iwb_map = get_item_warehouse_map(filters, sle)
	for group_by_key in iwb_map:
		item = group_by_key[1]
		warehouse = group_by_key[2]
		company = group_by_key[0]
		if item == '0032':
			frappe.msgprint(item)
	if not supplier:
		return [], []
    
	query = """
Select 
    i.item_code as item_code,
    i.item_name as item_name,
        case 
    when 
    (-1)*sold_items.sum > 0 then (-1)*sold_items.sum +bin.actual_qty 
    else  bin.actual_qty 
    end
    as Total_qty,
    case 
    when 
    (-1)*sold_items.sum < 0 then 0
    else (-1)*sold_items.sum 
    end as  total_qty_sold,
    case 
    when 
    (-1)*sold_items.sum < 0 then 0
    When (-1)*sold_items.sum > 0 then (-1)*sold_items.sum * ip.price_list_rate 

    end as   sold_amount,
    ip.price_list_rate as price,
    ((-1)*sold_items.sum + bin.actual_qty)* ip.price_list_rate as total_amount
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
    Order by i.item_code ASC
	"""
	data = frappe.db.sql(query, {"supplier": supplier,"from_date": from_date,"to_date": to_date}, as_dict=True)
	return columns, data



from frappe.utils import cint, date_diff, flt, getdate

from operator import itemgetter
from typing import Any, Dict, List, Optional, TypedDict
class StockBalanceFilter(TypedDict):
	company: Optional[str]
	from_date: str
	to_date: str
	item_group: Optional[str]
	item: Optional[str]
	warehouse: Optional[str]
	warehouse_type: Optional[str]
	include_uom: Optional[str]  # include extra info in converted UOM
	show_stock_ageing_data: bool
	show_variant_attributes: bool


SLEntry = Dict[str, Any]


def get_group_by_key(row, filters, inventory_dimension_fields) -> tuple:
	group_by_key = [row.company, row.item_code, row.warehouse]

	for fieldname in inventory_dimension_fields:
		if filters.get(fieldname):
			group_by_key.append(row.get(fieldname))

	return tuple(group_by_key)

def get_inventory_dimension_fields():
	return [dimension.fieldname for dimension in get_inventory_dimensions()]
def get_item_warehouse_map(filters, sle):
	iwb_map = {}
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))

	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	inventory_dimensions = get_inventory_dimension_fields()

	for d in sle:
		group_by_key = get_group_by_key(d, filters, inventory_dimensions)
		if group_by_key not in iwb_map:
			iwb_map[group_by_key] = frappe._dict(
				{
					"opening_qty": 0.0,
					"opening_val": 0.0,
					"in_qty": 0.0,
					"in_val": 0.0,
					"out_qty": 0.0,
					"out_val": 0.0,
					"bal_qty": 0.0,
					"bal_val": 0.0,
					"val_rate": 0.0,
				}
			)

		qty_dict = iwb_map[group_by_key]
		for field in inventory_dimensions:
			qty_dict[field] = d.get(field)

		if d.voucher_type == "Stock Reconciliation" and not d.batch_no:
			qty_diff = flt(d.qty_after_transaction) - flt(qty_dict.bal_qty)
		else:
			qty_diff = flt(d.actual_qty)

		value_diff = flt(d.stock_value_difference)

		if d.posting_date < from_date or (
			d.posting_date == from_date
			and d.voucher_type == "Stock Reconciliation"
			and frappe.db.get_value("Stock Reconciliation", d.voucher_no, "purpose") == "Opening Stock"
		):
			qty_dict.opening_qty += qty_diff
			qty_dict.opening_val += value_diff

		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(qty_diff, float_precision) >= 0:
				qty_dict.in_qty += qty_diff
				qty_dict.in_val += value_diff
			else:
				qty_dict.out_qty += abs(qty_diff)
				qty_dict.out_val += abs(value_diff)

		qty_dict.val_rate = d.valuation_rate
		qty_dict.bal_qty += qty_diff
		qty_dict.bal_val += value_diff

	return iwb_map


def get_stock_ledger_entries(filters: StockBalanceFilter, items: List[str]) -> List[SLEntry]:
	sle = frappe.qb.DocType("Stock Ledger Entry")

	query = (
		frappe.qb.from_(sle)
		.select(
			sle.item_code,
			sle.warehouse,
			sle.posting_date,
			sle.actual_qty,
			sle.valuation_rate,
			sle.company,
			sle.voucher_type,
			sle.qty_after_transaction,
			sle.stock_value_difference,
			sle.item_code.as_("name"),
			sle.voucher_no,
			sle.stock_value,
			sle.batch_no,
		)
		.where((sle.docstatus < 2) & (sle.is_cancelled == 0))
		.orderby(CombineDatetime(sle.posting_date, sle.posting_time))
		.orderby(sle.creation)
		.orderby(sle.actual_qty)
	)

	inventory_dimension_fields = get_inventory_dimension_fields()
	if inventory_dimension_fields:
		for fieldname in inventory_dimension_fields:
			query = query.select(fieldname)
			if fieldname in filters and filters.get(fieldname):
				query = query.where(sle[fieldname].isin(filters.get(fieldname)))

	if items:
		query = query.where(sle.item_code.isin(items))

	query = apply_conditions(query, filters)
	return query.run(as_dict=True)


def apply_conditions(query, filters):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	warehouse_table = frappe.qb.DocType("Warehouse")

	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if to_date := filters.get("to_date"):
		query = query.where(sle.posting_date <= to_date)
	else:
		frappe.throw(_("'To Date' is required"))

	if company := filters.get("company"):
		query = query.where(sle.company == company)

	if filters.get("warehouse"):
		query = apply_warehouse_filter(query, sle, filters)
	elif warehouse_type := filters.get("warehouse_type"):
		query = (
			query.join(warehouse_table)
			.on(warehouse_table.name == sle.warehouse)
			.where(warehouse_table.warehouse_type == warehouse_type)
		)

	return query