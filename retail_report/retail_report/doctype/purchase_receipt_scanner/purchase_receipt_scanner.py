# Copyright (c) 2026, alimerdanrahimov@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

# Items invented at the scanning bench get this prefix so they are easy to find
# and to block on later. Kept identical to the Client Script this replaces.
NEW_ITEM_PREFIX = "NEW_01"
NEW_ITEM_GROUP = "NEW_ITEMS"


class PurchaseReceiptScanner(Document):
	def validate(self):
		self.set_conversion_factors()
		self.merge_duplicate_rows()

	def set_conversion_factors(self):
		from erpnext.stock.get_item_details import get_conversion_factor

		for row in self.items:
			if row.conversion_factor:
				continue
			factor = get_conversion_factor(row.item_code, row.uom).get("conversion_factor")
			row.conversion_factor = factor or 1

	def merge_duplicate_rows(self):
		"""Collapse repeat scans of the same item/uom into one row.

		The scanner fires a row per scan, so a pallet of the same item arrives as
		N rows. Merging here rather than in the client keeps the desk form and the
		Vue page consistent.
		"""
		merged = {}
		for row in self.items:
			key = (row.item_code, row.uom)
			if key in merged:
				merged[key].qty = (merged[key].qty or 0) + (row.qty or 0)
				# A rate entered on any scan of the item wins over a blank one.
				if not merged[key].rate and row.rate:
					merged[key].rate = row.rate
			else:
				merged[key] = row

		if len(merged) != len(self.items):
			self.items = list(merged.values())
			for idx, row in enumerate(self.items, start=1):
				row.idx = idx

	@frappe.whitelist()
	def create_purchase_invoice(self):
		"""Turn the scanned list into a DRAFT Purchase Invoice.

		Deliberately a draft, and deliberately the only document this produces.
		Nothing reaches stock or valuation until back office has put the real
		rates on it and submitted - which is the whole point of the scan session
		being a scratch list rather than a stock document.

		update_stock is on because this invoice IS the goods receipt, matching how
		2,308 of the 2,450 invoices on this site already work.
		"""
		if self.purchase_invoice:
			frappe.throw(
				_("Purchase Invoice {0} has already been created from this scan.").format(
					self.purchase_invoice
				)
			)

		if not self.items:
			frappe.throw(_("No items scanned."))

		# Placeholder items are NOT blocked here - back office fixes the names on
		# the draft invoice. The gate sits on submit, where stock actually posts.
		# See retail_report.api.placeholder_guard.
		invoice = frappe.new_doc("Purchase Invoice")
		invoice.company = self.company
		invoice.supplier = self.supplier
		invoice.posting_date = self.date
		invoice.update_stock = 1
		invoice.set_warehouse = self.warehouse

		for row in self.items:
			invoice.append(
				"items",
				{
					"item_code": row.item_code,
					"qty": row.qty,
					"received_qty": row.qty,
					"uom": row.uom,
					"conversion_factor": row.conversion_factor or 1,
					"warehouse": self.warehouse,
					"rate": row.rate or 0,
					# The operator rarely knows the cost. A zero here is a placeholder
					# for back office to replace before submitting; the flag only stops
					# the draft from erroring while it sits unpriced.
					"allow_zero_valuation_rate": 0 if row.rate else 1,
				},
			)

		invoice.insert()

		self.db_set("purchase_invoice", invoice.name)
		return invoice.name
