# Copyright (c) 2026, alimerdanrahimov@gmail.com and contributors
# For license information, please see license.txt

"""Keeps scanner-invented items out of Purchase Invoices until someone completes them.

The warehouse operator scanning goods in cannot author item master data, so the
Purchase Receipt is allowed through with placeholder names — stock has to reflect
what physically arrived. The debt is collected one step later: whoever raises the
Purchase Invoice already has to supply the real rate, so they are the right person
to supply the real name and item group at the same time.
"""

import frappe
from frappe import _
from frappe.utils import escape_html

from retail_report.retail_report.doctype.purchase_receipt_scanner.purchase_receipt_scanner import (
	NEW_ITEM_GROUP,
	NEW_ITEM_PREFIX,
)


def find_placeholder_items(item_codes):
	"""Return items still carrying scanner placeholder data.

	Deliberately compares in Python rather than with SQL LIKE: `_` is a
	single-character wildcard there, so a `NEW_01%` pattern also matches names
	like `NEWx01…` — and a `NEW_%` pattern happily matches real products such as
	"Newa" and "Newtis".
	"""
	codes = [c for c in set(item_codes or []) if c]
	if not codes:
		return []

	rows = frappe.get_all(
		"Item",
		filters={"name": ("in", codes)},
		fields=["name", "item_name", "item_group"],
	)

	flagged = []
	for row in rows:
		reasons = []
		if (row.item_name or "").startswith(NEW_ITEM_PREFIX):
			reasons.append(_("name still says {0}").format(NEW_ITEM_PREFIX))
		if row.item_group == NEW_ITEM_GROUP:
			reasons.append(_("still in {0}").format(NEW_ITEM_GROUP))

		if reasons:
			flagged.append({"item_code": row.name, "item_name": row.item_name, "reasons": reasons})

	return flagged


def throw_placeholder_dialog(flagged):
	"""Raise the desk dialog listing what has to be fixed before retrying."""
	lines = []
	for item in flagged:
		lines.append(
			"<li><a href='/app/item/{code}' target='_blank'><b>{name}</b></a> "
			"<span style='color:#8d99a6'>({code}) — {reasons}</span></li>".format(
				code=escape_html(item["item_code"]),
				name=escape_html(item["item_name"] or item["item_code"]),
				reasons=escape_html(", ".join(item["reasons"])),
			)
		)

	frappe.throw(
		_("These items were created at the scanner and still need master data. "
		  "Open each one, set a real name and item group, then try again.")
		+ "<ul style='margin-top:8px'>{0}</ul>".format("".join(lines)),
		title=_("Items need master data"),
	)


def check_purchase_invoice(doc, method=None):
	"""doc_events hook on before_submit.

	Submit, not validate: the scanner creates the invoice as a draft precisely so
	back office can sit with it and fix things. Blocking the draft would block the
	handover itself. Submit is the moment stock and valuation actually post, so
	that is where the master data has to be sound.
	"""
	flagged = find_placeholder_items([row.item_code for row in doc.get("items") or []])
	if flagged:
		throw_placeholder_dialog(flagged)
