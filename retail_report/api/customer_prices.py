"""Customer-specific Item Prices, editable from the Purchase Invoice that sets them.

On the 5dogan-lineage sites the Purchase Invoice is a price-setting cockpit: goods come
in and every selling price list is written at receipt time. Customer-specific prices
were the one part of that story with no home - a `before_submit` popup listed them and
then bounced the operator to the Item Price list, mid-submit, losing the invoice.

This module backs a dialog on the invoice itself. It also records *which* invoice last
moved a customer price, which nothing did before, so the operator can tell a price they
just set from one that has been sitting there since March.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, now

# Written by `save_prices` so the dialog can badge each row by origin.
SOURCE_PI_FIELD = "custom_source_purchase_invoice"
SOURCE_ON_FIELD = "custom_source_updated_on"
PREVIOUS_RATE_FIELD = "custom_previous_rate"

# 373 of 377 customer-specific prices on 5dogan are on Optom, so it leads the list -
# but the operator can switch, unlike the legacy hardcoded-per-price-list scripts.
PREFERRED_PRICE_LIST = "Optom"


def is_enabled() -> bool:
	"""True only on sites that actually use special customers.

	`retail_report` is installed on five sites here, market1 included. None of them
	except 5dogan has this workflow, and none should grow a button for it.
	"""
	if not frappe.db.has_column("Customer", "special_customer"):
		return False
	return bool(frappe.db.count("Customer", {"special_customer": 1}))


def _provenance_available() -> bool:
	return frappe.db.has_column("Item Price", SOURCE_PI_FIELD)


@frappe.whitelist()
def feature_enabled():
	"""Cheap check the desk calls once per session before drawing the invoice button."""
	return is_enabled()


@frappe.whitelist()
def get_context(purchase_invoice=None, price_list=None):
	"""Everything the dialog renders, in one round trip."""
	if not is_enabled():
		frappe.throw(_("Special customers are not configured on this site."))

	frappe.has_permission("Item Price", "read", throw=True)

	customers = frappe.get_all(
		"Customer",
		filters={"special_customer": 1},
		fields=["name", "customer_name"],
		order_by="customer_name",
	)

	price_lists = [
		p.name
		for p in frappe.get_all(
			"Price List", filters={"enabled": 1, "selling": 1}, fields=["name"], order_by="name"
		)
	]
	if PREFERRED_PRICE_LIST in price_lists:
		price_lists.remove(PREFERRED_PRICE_LIST)
		price_lists.insert(0, PREFERRED_PRICE_LIST)

	price_list = price_list or (price_lists[0] if price_lists else None)
	items = _invoice_items(purchase_invoice)

	return {
		"enabled": True,
		"purchase_invoice": purchase_invoice,
		"price_list": price_list,
		"price_lists": price_lists,
		"customers": customers,
		"items": items,
		"rows": _price_rows([i["item_code"] for i in items], price_list, purchase_invoice),
		"has_provenance": _provenance_available(),
		"currency": frappe.db.get_value("Price List", price_list, "currency") if price_list else None,
	}


def _invoice_items(purchase_invoice):
	"""The invoice's items, each with the UOMs a price can be written against.

	Both the row UOM and the item's other conversions are offered: the legacy grid
	split unit from block by a hardcoded list of UOM names, which silently dropped any
	UOM nobody had thought to add to it.
	"""
	if not purchase_invoice:
		return []

	frappe.has_permission("Purchase Invoice", "read", doc=purchase_invoice, throw=True)

	rows = frappe.get_all(
		"Purchase Invoice Item",
		filters={"parent": purchase_invoice, "parenttype": "Purchase Invoice"},
		fields=["item_code", "item_name", "uom", "stock_uom", "qty", "rate", "conversion_factor"],
		order_by="idx",
	)

	items = {}
	for row in rows:
		item = items.setdefault(
			row.item_code,
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"stock_uom": row.stock_uom,
				"purchase_uom": row.uom,
				"purchase_rate": flt(row.rate),
				"qty": 0.0,
				"uoms": [],
			},
		)
		item["qty"] += flt(row.qty)

	for code, item in items.items():
		item["uoms"] = _ordered_uoms(code, item["stock_uom"], item["purchase_uom"])

	return list(items.values())


def _ordered_uoms(item_code, stock_uom, purchase_uom):
	"""The item's UOMs, smallest first, each with its conversion factor.

	Ordered by factor rather than by name so the single (шт, factor 1) always leads and
	the block (Koropka x20, Blok x15) follows - alphabetical put the Latin block names
	ahead of the Cyrillic single. Every UOM the item converts is returned, so an item
	with three of them gets three columns instead of being squeezed into the legacy
	two hardcoded name lists.
	"""
	factors = {}
	for row in frappe.get_all(
		"UOM Conversion Detail",
		filters={"parent": item_code, "parenttype": "Item"},
		fields=["uom", "conversion_factor"],
	):
		factors[row.uom] = flt(row.conversion_factor) or 1.0

	for uom in (stock_uom, purchase_uom):
		if uom:
			factors.setdefault(uom, 1.0)

	return [
		{"uom": uom, "conversion_factor": factor}
		for uom, factor in sorted(factors.items(), key=lambda kv: (kv[1], kv[0]))
	]


def _price_rows(item_codes, price_list, purchase_invoice):
	"""Existing prices for these items - customer-specific ones plus the general row.

	The general (customer-blank) rate rides along so the dialog can show what a special
	price is a discount *from*, and so % markup tools have a base to work off.
	"""
	if not item_codes or not price_list:
		return []

	fields = [
		"name",
		"item_code",
		"uom",
		"customer",
		"price_list",
		"price_list_rate",
		"currency",
		"valid_from",
		"valid_upto",
		"modified",
	]
	if frappe.db.has_column("Item Price", "bonus"):
		fields.append("bonus")
	if _provenance_available():
		fields += [SOURCE_PI_FIELD, SOURCE_ON_FIELD, PREVIOUS_RATE_FIELD]

	records = frappe.get_all(
		"Item Price",
		filters={"item_code": ["in", item_codes], "price_list": price_list},
		fields=fields,
		limit_page_length=0,
		order_by="item_code, uom, customer",
	)

	rows = []
	for r in records:
		source_pi = r.get(SOURCE_PI_FIELD)
		rows.append(
			{
				"name": r.name,
				"item_code": r.item_code,
				"uom": r.uom,
				"customer": r.customer or None,
				"price_list": r.price_list,
				"rate": flt(r.price_list_rate),
				"bonus": flt(r.get("bonus")),
				"currency": r.currency,
				"valid_from": r.valid_from,
				"valid_upto": r.valid_upto,
				"modified": r.modified,
				"source_purchase_invoice": source_pi,
				"source_updated_on": r.get(SOURCE_ON_FIELD),
				"previous_rate": flt(r.get(PREVIOUS_RATE_FIELD)) if r.get(PREVIOUS_RATE_FIELD) else None,
				# The question the operator actually asks: did *this* invoice do that?
				"changed_by_this_invoice": bool(source_pi and source_pi == purchase_invoice),
			}
		)
	return rows


@frappe.whitelist()
def save_prices(purchase_invoice, changes):
	"""Upsert a batch of customer-specific prices, stamped with their source invoice.

	One call for the whole grid. The legacy dialog fired one request per UOM and looped
	customers server-side, so a 4-UOM x 43-customer edit was 4 sequential round trips
	behind a progress bar; the counts here are the same but the waiting is not.
	"""
	if not is_enabled():
		frappe.throw(_("Special customers are not configured on this site."))

	frappe.has_permission("Item Price", "write", throw=True)

	if isinstance(changes, str):
		changes = json.loads(changes)
	if not changes:
		return {"created": [], "updated": [], "unchanged": 0}

	if purchase_invoice:
		frappe.has_permission("Purchase Invoice", "read", doc=purchase_invoice, throw=True)

	special = {
		c.name for c in frappe.get_all("Customer", filters={"special_customer": 1}, fields=["name"])
	}
	stamp = _provenance_available()
	timestamp = now()

	created, updated, unchanged = [], [], 0

	for change in changes:
		customer = change.get("customer")
		if customer not in special:
			frappe.throw(_("{0} is not a special customer.").format(customer or "?"))

		rate = flt(change.get("rate"))
		if rate <= 0:
			frappe.throw(
				_("Rate must be greater than zero for {0} / {1}.").format(change.get("item_code"), customer)
			)

		# `bonus` defaults to 1 on these sites, so an unset bonus reads as a real
		# promotion downstream. Always write it explicitly.
		bonus = flt(change.get("bonus"))

		filters = {
			"item_code": change.get("item_code"),
			"price_list": change.get("price_list"),
			"uom": change.get("uom"),
			"customer": customer,
		}
		existing = frappe.db.exists("Item Price", filters)

		if existing:
			doc = frappe.get_doc("Item Price", existing)
			if flt(doc.price_list_rate) == rate and flt(doc.get("bonus")) == bonus:
				unchanged += 1
				continue
			if stamp:
				doc.set(PREVIOUS_RATE_FIELD, flt(doc.price_list_rate))
			doc.price_list_rate = rate
			doc.set("bonus", bonus)
			if stamp:
				doc.set(SOURCE_PI_FIELD, purchase_invoice)
				doc.set(SOURCE_ON_FIELD, timestamp)
			doc.save()
			updated.append(doc.name)
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": change.get("item_code"),
					"price_list": change.get("price_list"),
					"uom": change.get("uom"),
					"customer": customer,
					"price_list_rate": rate,
					"bonus": bonus,
				}
			)
			if stamp:
				doc.set(SOURCE_PI_FIELD, purchase_invoice)
				doc.set(SOURCE_ON_FIELD, timestamp)
			doc.insert()
			created.append(doc.name)

	return {
		"created": created,
		"updated": updated,
		"unchanged": unchanged,
		"total": len(created) + len(updated),
	}
