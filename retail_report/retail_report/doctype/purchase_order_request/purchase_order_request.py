# Copyright (c) 2026, Alimerdan Rahimov and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt


class PurchaseOrderRequest(Document):
	def validate(self):
		total_qty = 0.0
		total_weight = 0.0

		for row in self.items:
			row.total_weight = flt(row.qty) * flt(row.conversion_factor or 1) * flt(row.weight_per_unit)
			total_qty += flt(row.qty)
			total_weight += flt(row.total_weight)

		self.total_qty = total_qty
		self.total_weight = total_weight

	def on_submit(self):
		self.db_set("status", "Submitted")

	def on_cancel(self):
		self.db_set("status", "Cancelled")


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_uom_query(doctype, txt, searchfield, start, page_len, filters):
	item_code = filters.get("item_code")
	if not item_code:
		return []

	stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")

	return frappe.db.sql(
		"""
		select uom from (
			select uom from `tabUOM Conversion Detail` where parent = %(item_code)s
			union
			select %(stock_uom)s as uom
		) as item_uoms
		where uom like %(txt)s
		limit %(start)s, %(page_len)s
		""",
		{
			"item_code": item_code,
			"stock_uom": stock_uom,
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)


@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.supplier = source.supplier or ""
		target.schedule_date = source.schedule_date
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source, target, source_parent):
		target.qty = source.qty
		target.uom = source.uom
		target.conversion_factor = source.conversion_factor or 1
		target.schedule_date = source.schedule_date

	doclist = get_mapped_doc(
		"Purchase Order Request",
		source_name,
		{
			"Purchase Order Request": {
				"doctype": "Purchase Order",
				"field_map": {"name": "purchase_order_request"},
				"validation": {"docstatus": ["=", 1]},
			},
			"Purchase Order Request Item": {
				"doctype": "Purchase Order Item",
				"field_map": {
					"name": "purchase_order_request_item",
					"parent": "purchase_order_request",
				},
				"postprocess": update_item,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def update_request_on_po_submit(doc, method):
	if doc.get("purchase_order_request"):
		request = frappe.get_doc("Purchase Order Request", doc.purchase_order_request)
		request.db_set("status", "Ordered")


@frappe.whitelist()
def update_request_on_po_cancel(doc, method):
	if doc.get("purchase_order_request"):
		request = frappe.get_doc("Purchase Order Request", doc.purchase_order_request)
		request.db_set("status", "Submitted")
