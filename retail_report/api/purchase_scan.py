# Copyright (c) 2026, alimerdanrahimov@gmail.com and contributors
# For license information, please see license.txt

"""Server endpoints for the mobile Purchase Receipt scanner page.

The Client Script this replaces did item lookup, UOM resolution and Item creation
straight from the browser, one round-trip per row. On a phone over mobile data
that is the whole latency budget, so each operator action gets exactly one call
here instead.
"""

import frappe
from frappe import _

from retail_report.retail_report.doctype.purchase_receipt_scanner.purchase_receipt_scanner import (
	NEW_ITEM_GROUP,
	NEW_ITEM_PREFIX,
)

SCANNER_DOCTYPE = "Purchase Receipt Scanner"


def _check_permission(ptype="write"):
	if not frappe.has_permission(SCANNER_DOCTYPE, ptype):
		frappe.throw(_("Not permitted to use the Purchase Receipt scanner."), frappe.PermissionError)


def _item_payload(item_code, barcode=None, scanned_uom=None):
	"""Everything the qty sheet needs about an item, in one shot."""
	item = frappe.get_cached_doc("Item", item_code)

	uoms = [item.stock_uom]
	for row in item.uoms or []:
		if row.uom and row.uom not in uoms:
			uoms.append(row.uom)

	return {
		"found": True,
		"item_code": item.name,
		"item_name": item.item_name,
		"stock_uom": item.stock_uom,
		"uoms": uoms,
		"uom": scanned_uom or item.stock_uom,
		"barcode": barcode or "",
		"last_purchase_rate": item.last_purchase_rate or 0,
		"image": item.image or "",
		"is_placeholder": (item.item_name or "").startswith(NEW_ITEM_PREFIX),
	}


@frappe.whitelist()
def scan_lookup(code):
	"""Resolve a scanned barcode (or a typed item code) to a full item payload."""
	_check_permission("read")

	code = (code or "").strip()
	if not code:
		frappe.throw(_("Nothing scanned."))

	barcode_row = frappe.db.get_value(
		"Item Barcode", {"barcode": code}, ["parent", "uom"], as_dict=True
	)
	if barcode_row and barcode_row.parent:
		return _item_payload(barcode_row.parent, barcode=code, scanned_uom=barcode_row.uom)

	if frappe.db.exists("Item", code):
		return _item_payload(code, barcode=code)

	return {"found": False, "barcode": code}


@frappe.whitelist()
def search_items(query, limit=20):
	"""Typeahead over the item master for the manual-entry fallback."""
	_check_permission("read")

	query = (query or "").strip()
	if not query:
		return []

	like = "%{0}%".format(query)
	return frappe.get_all(
		"Item",
		filters={"disabled": 0, "is_purchase_item": 1},
		or_filters={"name": ("like", like), "item_name": ("like", like)},
		fields=["name as item_code", "item_name", "stock_uom"],
		limit_page_length=frappe.utils.cint(limit) or 20,
		order_by="modified desc",
	)


@frappe.whitelist()
def create_item(item_name, uom, barcode=None, item_code=None):
	"""Mint a placeholder Item for stock that arrived without a known barcode.

	Named with the NEW_ prefix on purpose: the invoice cannot be submitted while any
	placeholder is still unnamed, which is what stops these leaking into the item
	master unnoticed. See retail_report.api.placeholder_guard.
	"""
	_check_permission("create")

	item_name = (item_name or "").strip()
	if not item_name:
		frappe.throw(_("Item name is required."))

	barcode = (barcode or "").strip()
	code = barcode or (item_code or "").strip()
	if not code:
		code = frappe.generate_hash("nb", 8).upper()
		code = "NB-" + code

	if frappe.db.exists("Item", code):
		frappe.throw(_("Item {0} already exists.").format(code))

	if not frappe.db.exists("Item Group", NEW_ITEM_GROUP):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": NEW_ITEM_GROUP,
				"parent_item_group": frappe.db.get_value("Item Group", {"is_group": 1}, "name"),
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": code,
			"item_name": "{0} {1}".format(NEW_ITEM_PREFIX, item_name),
			"item_group": NEW_ITEM_GROUP,
			"stock_uom": uom,
			"is_stock_item": 1,
			"is_purchase_item": 1,
		}
	)
	if barcode:
		item.append("barcodes", {"barcode": barcode})

	item.insert()

	payload = _item_payload(item.name, barcode=barcode)
	payload["created"] = True
	return payload


@frappe.whitelist()
def save_session(doc):
	"""Create or update the scan session, returning the stored state."""
	_check_permission("write")

	if isinstance(doc, str):
		doc = frappe.parse_json(doc)

	if doc.get("name") and frappe.db.exists(SCANNER_DOCTYPE, doc["name"]):
		session = frappe.get_doc(SCANNER_DOCTYPE, doc["name"])
		session.update(
			{
				"supplier": doc.get("supplier"),
				"company": doc.get("company"),
				"warehouse": doc.get("warehouse"),
				"date": doc.get("date"),
			}
		)
		session.set("items", [])
	else:
		session = frappe.new_doc(SCANNER_DOCTYPE)
		session.update(
			{
				"supplier": doc.get("supplier"),
				"company": doc.get("company"),
				"warehouse": doc.get("warehouse"),
				"date": doc.get("date"),
			}
		)

	for row in doc.get("items") or []:
		session.append(
			"items",
			{
				"item_code": row.get("item_code"),
				"item_name": row.get("item_name"),
				"qty": row.get("qty"),
				"uom": row.get("uom"),
				"rate": row.get("rate") or 0,
				"barcode": row.get("barcode"),
				"is_new_item": row.get("is_new_item") or 0,
			},
		)

	session.save()
	return session.as_dict()


@frappe.whitelist()
def create_invoice(name):
	"""Turn a saved scan session into a draft Purchase Invoice."""
	_check_permission("write")

	session = frappe.get_doc(SCANNER_DOCTYPE, name)
	invoice_name = session.create_purchase_invoice()

	return {
		"purchase_invoice": invoice_name,
		"route": "/app/purchase-invoice/{0}".format(invoice_name),
	}


@frappe.whitelist()
def get_defaults():
	"""Company/warehouse defaults so the operator starts with fields prefilled."""
	_check_permission("read")

	company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default(
		"company"
	)
	warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")

	# This bench runs more than one company, so the operator has to be able to
	# switch rather than inherit a single global default silently.
	companies = frappe.get_all("Company", pluck="name", order_by="name")

	return {
		"company": company or (companies[0] if companies else None),
		"companies": companies,
		"warehouse": warehouse,
		"date": frappe.utils.nowdate(),
		"currency": frappe.db.get_value("Company", company, "default_currency") if company else None,
	}
