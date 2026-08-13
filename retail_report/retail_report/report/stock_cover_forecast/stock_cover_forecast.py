# Copyright (c) 2026, and contributors
# For license information, please see license.txt

import hashlib
import json
import math
import statistics
from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, flt, getdate, nowdate
from frappe.utils.nestedset import get_descendants_of

# Reuse the same status/color config already used by "Stock Balance Reorder"
# (Report Settings > Report Settings Table) instead of inventing a new one.
STATUS_CRITICAL = "Limit Attention"
STATUS_LOW = "Limit Warning"
STATUS_OK = "Limit OK"

# ABC: cumulative revenue-contribution cutoffs (standard 80/15/5 Pareto split).
ABC_CUTOFF_A = 80
ABC_CUTOFF_B = 95

# XYZ: coefficient-of-variation cutoffs for monthly demand (textbook default).
# X = steady demand, Y = fluctuating, Z = sporadic/unpredictable.
XYZ_CUTOFF_X = 0.5
XYZ_CUTOFF_Y = 1.0

# The purchase-request workflow makes several server calls in a row (supplier
# list -> items per supplier -> refresh after each created request). The rows
# and supplier history barely change within that window, so they are cached
# per filter-set instead of recomputed from scratch on every click.
WORKFLOW_CACHE_TTL = 10 * 60


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
		{
			"label": _("Item Group"),
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 120,
		},
		{
			"label": _("ABC"),
			"fieldname": "abc_category",
			"fieldtype": "Data",
			"width": 60,
		},
		{
			"label": _("XYZ"),
			"fieldname": "xyz_category",
			"fieldtype": "Data",
			"width": 60,
		},
		{"label": _("Stock UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 90},
		{"label": _("Qty Sold in Period"), "fieldname": "qty_sold", "fieldtype": "Float", "width": 120},
		{
			"label": _("Typical Daily Demand"),
			"fieldname": "avg_daily_demand",
			"fieldtype": "Float",
			"precision": 3,
			"width": 130,
		},
		{"label": _("Current Stock"), "fieldname": "current_stock", "fieldtype": "Float", "width": 110},
		{
			"label": _("Days of Stock Remaining"),
			"fieldname": "days_of_stock",
			"fieldtype": "HTML",
			"width": 170,
		},
	]


def get_data(filters):
	rows, _critical_days, _low_days = compute_rows(filters)
	color_map = get_status_colors()

	data = []
	for row in rows:
		status = row.pop("status")
		row["days_of_stock"] = render_days_of_stock(row["days_of_stock"], status, color_map)
		data.append(row)

	return data


def compute_rows(filters):
	"""Shared by the report view and the Purchase Order Request endpoints below -
	returns raw (unrendered) rows plus the resolved critical/low thresholds."""
	from_date, to_date = get_period(filters)
	critical_days = flt(filters.get("critical_days")) or 1
	low_days = flt(filters.get("low_days")) or 5

	if low_days <= critical_days:
		frappe.throw(_("'Low Stock' day threshold must be greater than the 'Critical' day threshold"))

	sales_map, revenue_map, daily_qty_map, monthly_qty_map = get_sales_history(filters, from_date, to_date)
	stock_map = get_current_stock(filters)
	item_codes = set(sales_map) | set(stock_map)
	item_details = get_item_details(item_codes)

	period_buckets = get_period_buckets(from_date, to_date)
	abc_map = classify_abc(revenue_map)
	xyz_map = classify_xyz(monthly_qty_map, period_buckets)

	rows = []
	for item_code, item in item_details.items():
		qty_sold = flt(sales_map.get(item_code))
		current_stock = flt(stock_map.get(item_code))

		# Nothing sold and nothing in stock - not relevant to a demand/stock report.
		if not qty_sold and not current_stock:
			continue

		# Median of qty sold on days it actually sold - not total / calendar days.
		# A flat calendar-day average is skewed both by non-selling days (understates
		# the item's real per-sale demand) and by one-off bulk orders (a mean would
		# be dragged way up by a single huge day; the median ignores it).
		daily_values = daily_qty_map.get(item_code, [])
		avg_daily_demand = statistics.median(daily_values) if daily_values else 0

		# An item that sold at all is never treated as demanding less than 1/day -
		# avoids meaningless "thousands of days remaining" results for rare sellers.
		if qty_sold > 0:
			avg_daily_demand = max(avg_daily_demand, 1)
		days_of_stock = current_stock / avg_daily_demand if avg_daily_demand > 0 else None

		rows.append(
			{
				"item_code": item_code,
				"item_name": item.item_name,
				"item_group": item.item_group,
				"abc_category": abc_map.get(item_code, "C"),
				"xyz_category": xyz_map.get(item_code, "Z"),
				"stock_uom": item.stock_uom,
				"qty_sold": qty_sold,
				"avg_daily_demand": avg_daily_demand,
				"current_stock": current_stock,
				"days_of_stock": days_of_stock,
				"status": get_status(days_of_stock, critical_days, low_days),
			}
		)

	rows.sort(key=lambda r: r["days_of_stock"] if r["days_of_stock"] is not None else 999999)
	return rows, critical_days, low_days


def get_status(days_of_stock, critical_days, low_days):
	if days_of_stock is None:
		return None
	if days_of_stock < critical_days:
		return STATUS_CRITICAL
	if days_of_stock < low_days:
		return STATUS_LOW
	return STATUS_OK


def render_days_of_stock(days_of_stock, status, color_map):
	if days_of_stock is None:
		return _("No Sales in Period")

	color = color_map.get(status) or "#29CD42"
	return (
		"<span style='display:inline-block;min-width:70px;text-align:center;"
		f"padding:2px 8px;border-radius:3px;background-color:{color}'>"
		f"{flt(days_of_stock, 1)}"
		"</span>"
	)


def get_status_colors():
	rows = frappe.get_all(
		"Report Settings Table",
		filters={"status": ("in", [STATUS_CRITICAL, STATUS_LOW, STATUS_OK])},
		fields=["status", "color"],
	)
	return {row.status: row.color for row in rows}


def get_period(filters):
	to_date = getdate(filters.get("to_date") or nowdate())
	from_date = getdate(filters.get("from_date")) if filters.get("from_date") else add_days(to_date, -180)

	if from_date > to_date:
		frappe.throw(_("From Date cannot be after To Date"))

	return from_date, to_date


def get_item_group_condition(item_group):
	children = get_descendants_of("Item Group", item_group, ignore_permissions=True)
	return children + [item_group]


def build_sales_conditions(filters, from_date, to_date):
	conditions = ["si.docstatus = 1", "si.posting_date between %(from_date)s and %(to_date)s"]
	params = {"from_date": from_date, "to_date": to_date}

	if filters.get("company"):
		conditions.append("si.company = %(company)s")
		params["company"] = filters.company
	if filters.get("item_code"):
		conditions.append("sii.item_code = %(item_code)s")
		params["item_code"] = filters.item_code
	if filters.get("item_group"):
		conditions.append("sii.item_group in %(item_groups)s")
		params["item_groups"] = tuple(get_item_group_condition(filters.item_group))

	return conditions, params


def get_sales_history(filters, from_date, to_date):
	"""Every sales-derived input in ONE sweep of Sales Invoice Item, grouped by
	item and posting date: total qty sold (demand), revenue (ABC), per-day qty
	(median daily demand) and per-month qty (XYZ) all derive from the same rows.
	This used to be three separate scans of the invoice table and dominated the
	report's runtime.

	Uses stock_qty, not qty: a line sold in a non-stock UOM (e.g. "Box" of 12)
	records qty=1 but consumes 12 stock units - stock_qty is qty * conversion_factor,
	the only figure comparable to Bin.actual_qty. revenue stays on qty * rate since
	rate is per the transaction UOM, so the amount is already UOM-invariant.
	"""
	conditions, params = build_sales_conditions(filters, from_date, to_date)

	rows = frappe.db.sql(
		f"""
		select sii.item_code, si.posting_date,
			sum(sii.stock_qty) as qty, sum(sii.qty * sii.rate) as revenue
		from `tabSales Invoice Item` sii
		inner join `tabSales Invoice` si on si.name = sii.parent
		where {" and ".join(conditions)}
		group by sii.item_code, si.posting_date
		""",
		params,
		as_dict=True,
	)

	sales_map = defaultdict(float)
	revenue_map = defaultdict(float)
	daily_qty_map = defaultdict(list)
	monthly_qty_map = defaultdict(lambda: defaultdict(float))

	for row in rows:
		qty = flt(row.qty)
		sales_map[row.item_code] += qty
		revenue_map[row.item_code] += flt(row.revenue)
		daily_qty_map[row.item_code].append(qty)
		monthly_qty_map[row.item_code][row.posting_date.strftime("%Y-%m")] += qty

	return (
		dict(sales_map),
		dict(revenue_map),
		dict(daily_qty_map),
		{item_code: dict(periods) for item_code, periods in monthly_qty_map.items()},
	)


def get_period_buckets(from_date, to_date):
	"""List of 'YYYY-MM' calendar months spanned by the report's date range."""
	buckets = []
	cursor = from_date.replace(day=1)
	last = to_date.replace(day=1)

	while cursor <= last:
		buckets.append(cursor.strftime("%Y-%m"))
		cursor = cursor.replace(year=cursor.year + 1, month=1) if cursor.month == 12 else cursor.replace(month=cursor.month + 1)

	return buckets


def classify_abc(revenue_map):
	"""A/B/C by cumulative revenue contribution (standard Pareto 80/15/5 split)."""
	total_revenue = sum(revenue_map.values())
	if not total_revenue:
		return {}

	ranked = sorted(revenue_map.items(), key=lambda x: x[1], reverse=True)

	abc_map = {}
	cumulative = 0.0
	for item_code, revenue in ranked:
		cumulative += revenue
		cumulative_pct = (cumulative / total_revenue) * 100
		if cumulative_pct <= ABC_CUTOFF_A:
			abc_map[item_code] = "A"
		elif cumulative_pct <= ABC_CUTOFF_B:
			abc_map[item_code] = "B"
		else:
			abc_map[item_code] = "C"

	return abc_map


def classify_xyz(monthly_qty_map, period_buckets):
	"""X/Y/Z by coefficient of variation of monthly demand (steady -> sporadic)."""
	num_periods = len(period_buckets)
	xyz_map = {}

	for item_code, period_qty in monthly_qty_map.items():
		# Fewer than 2 periods isn't enough history to judge consistency.
		if num_periods < 2:
			xyz_map[item_code] = "Z"
			continue

		values = [period_qty.get(period, 0) for period in period_buckets]
		mean = sum(values) / num_periods
		if not mean:
			xyz_map[item_code] = "Z"
			continue

		variance = sum((v - mean) ** 2 for v in values) / num_periods
		coefficient_of_variation = math.sqrt(variance) / mean

		if coefficient_of_variation <= XYZ_CUTOFF_X:
			xyz_map[item_code] = "X"
		elif coefficient_of_variation <= XYZ_CUTOFF_Y:
			xyz_map[item_code] = "Y"
		else:
			xyz_map[item_code] = "Z"

	return xyz_map


def get_current_stock(filters):
	bin_ = frappe.qb.DocType("Bin")
	query = frappe.qb.from_(bin_).select(bin_.item_code, Sum(bin_.actual_qty).as_("actual_qty")).groupby(bin_.item_code)

	if filters.get("company"):
		warehouse = frappe.qb.DocType("Warehouse")
		query = query.join(warehouse).on(warehouse.name == bin_.warehouse).where(warehouse.company == filters.company)

	if filters.get("item_code"):
		query = query.where(bin_.item_code == filters.item_code)

	return {row.item_code: flt(row.actual_qty) for row in query.run(as_dict=True)}


def get_item_details(item_codes):
	if not item_codes:
		return {}

	item = frappe.qb.DocType("Item")
	query = (
		frappe.qb.from_(item)
		.select(item.name, item.item_name, item.item_group, item.stock_uom)
		.where(item.name.isin(list(item_codes)))
		.where(item.is_stock_item == 1)
		.where(item.disabled == 0)
	)

	return {row.name: row for row in query.run(as_dict=True)}


# ---------------------------------------------------------------------------
# "Create Purchase Requests" button: group red/yellow items by their most
# recent supplier (from Purchase Invoice history) and draft a Purchase Order
# Request per supplier from the items the user picks.
# ---------------------------------------------------------------------------

NO_SUPPLIER_LABEL = "No Supplier History"


def check_purchase_request_permission():
	if not frappe.has_permission("Purchase Order Request", "create"):
		frappe.throw(_("You are not permitted to create Purchase Order Requests"), frappe.PermissionError)


def parse_filters(filters):
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	return frappe._dict(filters or {})


def get_workflow_cache_key(filters):
	relevant = {
		key: str(filters.get(key) or "")
		for key in ("company", "from_date", "to_date", "item_group", "item_code", "critical_days", "low_days")
	}
	digest = hashlib.sha1(json.dumps(relevant, sort_keys=True).encode()).hexdigest()[:16]
	return f"stock_cover_forecast_at_risk:{digest}"


def get_at_risk_state(filters):
	"""At-risk rows + latest-supplier map for the purchase-request workflow,
	cached per filter-set (see WORKFLOW_CACHE_TTL). The already-requested
	exclusion is deliberately NOT part of the cached state - it must stay live
	so items drop out of the dialogs the moment their request is created."""
	cache_key = get_workflow_cache_key(filters)
	# expires=True: without it a cache MISS gets memoized as None in
	# frappe.local.cache and every later lookup in the process recomputes.
	state = frappe.cache().get_value(cache_key, expires=True)

	if state is None:
		rows, _critical_days, low_days = compute_rows(filters)
		at_risk = [row for row in rows if row["status"] in (STATUS_CRITICAL, STATUS_LOW)]
		supplier_map = get_latest_suppliers([row["item_code"] for row in at_risk], filters.get("company"))
		state = {"at_risk": at_risk, "low_days": low_days, "supplier_map": supplier_map}
		frappe.cache().set_value(cache_key, state, expires_in_sec=WORKFLOW_CACHE_TTL)

	return state


def get_at_risk_rows(filters):
	"""Red/yellow rows, minus items that already have an open Purchase Order
	Request - re-suggesting those would risk ordering the same shortfall twice."""
	state = get_at_risk_state(filters)
	at_risk = state["at_risk"]

	already_requested = get_already_requested_items([row["item_code"] for row in at_risk])
	skipped_count = sum(1 for row in at_risk if row["item_code"] in already_requested)
	at_risk = [row for row in at_risk if row["item_code"] not in already_requested]

	return at_risk, state["low_days"], state["supplier_map"], skipped_count


def get_already_requested_items(item_codes):
	"""Item codes that already have a non-cancelled Purchase Order Request."""
	if not item_codes:
		return set()

	rows = frappe.db.sql(
		"""
		select distinct pori.item_code
		from `tabPurchase Order Request Item` pori
		inner join `tabPurchase Order Request` por on por.name = pori.parent
		where por.status != 'Cancelled' and pori.item_code in %(item_codes)s
		""",
		{"item_codes": tuple(item_codes)},
		as_dict=True,
	)

	return {row.item_code for row in rows}


def get_excluded_suppliers():
	"""Suppliers flagged via Supplier.exclude_from_reorder_suggestions - never
	suggested by the workflow below, even if they're an item's most recent supplier."""
	return set(frappe.get_all("Supplier", filters={"exclude_from_reorder_suggestions": 1}, pluck="name"))


def get_latest_suppliers(item_codes, company=None):
	"""Most recent non-excluded supplier per item, from submitted Purchase Invoice
	history. An item whose entire purchase history is excluded suppliers gets no
	supplier here (falls through to "No Supplier History" for manual assignment)."""
	if not item_codes:
		return {}

	excluded_suppliers = get_excluded_suppliers()

	conditions = ["pi.docstatus = 1", "pii.item_code in %(item_codes)s"]
	params = {"item_codes": tuple(item_codes)}

	if company:
		conditions.append("pi.company = %(company)s")
		params["company"] = company

	rows = frappe.db.sql(
		f"""
		select pii.item_code, pi.supplier, pi.posting_date, pi.creation
		from `tabPurchase Invoice Item` pii
		inner join `tabPurchase Invoice` pi on pi.name = pii.parent
		where {" and ".join(conditions)}
		order by pi.posting_date desc, pi.creation desc
		""",
		params,
		as_dict=True,
	)

	supplier_map = {}
	for row in rows:
		if row.supplier in excluded_suppliers:
			continue
		# Rows are ordered most-recent-first; keep only the first (latest) supplier seen.
		supplier_map.setdefault(row.item_code, row.supplier)

	return supplier_map


def get_order_uoms(item_codes):
	"""Preferred ordering UOM per item, e.g. Koropka = 10 шт: Item.purchase_uom
	if set, else the item's secondary UOM with conversion_factor > 1 from its
	UOM Conversion table. Items without one are ordered in stock UOM."""
	if not item_codes:
		return {}

	rows = frappe.db.sql(
		"""
		select ucd.parent as item_code, ucd.uom, ucd.conversion_factor
		from `tabUOM Conversion Detail` ucd
		inner join `tabItem` i on i.name = ucd.parent
		where ucd.parent in %(item_codes)s
			and ucd.uom != i.stock_uom
			and ucd.conversion_factor > 1
			and (ifnull(i.purchase_uom, '') = '' or i.purchase_uom = ucd.uom)
		order by ucd.idx
		""",
		{"item_codes": tuple(item_codes)},
		as_dict=True,
	)

	order_uom_map = {}
	for row in rows:
		# Should an item ever define several bigger UOMs, keep the first by idx.
		order_uom_map.setdefault(row.item_code, {"uom": row.uom, "conversion_factor": flt(row.conversion_factor)})

	return order_uom_map


def to_order_uom(stock_qty, uom_info, stock_uom):
	"""Convert a suggested qty in stock UOM to the ordering UOM, rounding UP to
	whole packs (97 шт at 10/Koropka -> 10 Koropka) so a shortfall is never
	under-ordered."""
	if not uom_info:
		return stock_qty, stock_uom, 1

	factor = uom_info["conversion_factor"]
	return math.ceil(stock_qty / factor), uom_info["uom"], factor


def get_cover_days(filters):
	"""Per-ABC-class order coverage days from the report filters. A class whose
	value is empty/0 falls back to the top-up-to-low-threshold suggestion."""
	return {
		"A": flt(filters.get("cover_days_a")),
		"B": flt(filters.get("cover_days_b")),
		"C": flt(filters.get("cover_days_c")),
	}


def suggest_qty(row, low_days, cover_days=None):
	days = (cover_days or {}).get(row.get("abc_category"))
	if days:
		# Order size = N days of typical demand, N configured per ABC class.
		return math.ceil(max(days * row["avg_daily_demand"], 1))

	target_stock = low_days * row["avg_daily_demand"]
	return math.ceil(max(target_stock - row["current_stock"], row["avg_daily_demand"], 1))


@frappe.whitelist()
def get_at_risk_suppliers(filters=None):
	"""Suppliers for currently red/yellow items, with a critical/low breakdown so
	the most urgent suppliers (more red items) sort first, not just the biggest list."""
	check_purchase_request_permission()
	filters = parse_filters(filters)

	at_risk_rows, _low_days, supplier_map, skipped_count = get_at_risk_rows(filters)

	counts = defaultdict(lambda: {"critical_count": 0, "low_count": 0})
	for row in at_risk_rows:
		supplier = supplier_map.get(row["item_code"], NO_SUPPLIER_LABEL)
		key = "critical_count" if row["status"] == STATUS_CRITICAL else "low_count"
		counts[supplier][key] += 1

	suppliers = [
		{
			"supplier": supplier,
			"critical_count": c["critical_count"],
			"low_count": c["low_count"],
			"item_count": c["critical_count"] + c["low_count"],
		}
		for supplier, c in counts.items()
	]
	suppliers.sort(key=lambda d: (d["critical_count"], d["item_count"]), reverse=True)

	return {"suppliers": suppliers, "skipped_count": skipped_count}


@frappe.whitelist()
def get_at_risk_items_for_supplier(filters=None, supplier=None):
	"""Red/yellow items whose most recent supplier matches the given supplier,
	with a suggested reorder qty (enough to reach the Low Stock Threshold buffer)."""
	check_purchase_request_permission()
	filters = parse_filters(filters)

	at_risk_rows, low_days, supplier_map, _skipped_count = get_at_risk_rows(filters)
	cover_days = get_cover_days(filters)

	matched = [row for row in at_risk_rows if supplier_map.get(row["item_code"], NO_SUPPLIER_LABEL) == supplier]
	order_uoms = get_order_uoms([row["item_code"] for row in matched])

	result = []
	for row in matched:
		stock_qty = suggest_qty(row, low_days, cover_days)
		order_qty, order_uom, conversion_factor = to_order_uom(
			stock_qty, order_uoms.get(row["item_code"]), row["stock_uom"]
		)

		result.append(
			{
				"item_code": row["item_code"],
				"item_name": row["item_name"],
				"stock_uom": row["stock_uom"],
				"current_stock": row["current_stock"],
				"avg_daily_demand": row["avg_daily_demand"],
				"days_of_stock": row["days_of_stock"],
				"status": row["status"],
				"abc_category": row["abc_category"],
				"xyz_category": row["xyz_category"],
				"negative_stock": row["current_stock"] < 0,
				"suggested_qty": order_qty,
				"uom": order_uom,
				"conversion_factor": conversion_factor,
			}
		)

	return result


@frappe.whitelist()
def create_purchase_order_request(company, supplier, items):
	check_purchase_request_permission()

	if isinstance(items, str):
		items = frappe.parse_json(items)
	if not items:
		frappe.throw(_("Select at least one item"))

	doc = frappe.new_doc("Purchase Order Request")
	doc.company = company
	doc.schedule_date = nowdate()
	if supplier and supplier != NO_SUPPLIER_LABEL:
		doc.supplier = supplier

	for item in items:
		doc.append(
			"items",
			{
				"item_code": item.get("item_code"),
				"qty": flt(item.get("qty")) or 1,
				"uom": item.get("uom"),
				"conversion_factor": flt(item.get("conversion_factor")) or 1,
			},
		)

	doc.insert()
	return doc.name


@frappe.whitelist()
def create_purchase_order_requests_for_all_suppliers(filters=None):
	"""Bulk path for the analyst workflow: one draft Purchase Order Request per
	supplier, using the suggested quantities as-is (no per-item review). Items
	with no supplier history are skipped - they can't be auto-ordered without
	knowing who to buy from, and are reported back so a human can handle them."""
	check_purchase_request_permission()
	filters = parse_filters(filters)

	at_risk_rows, low_days, supplier_map, skipped_count = get_at_risk_rows(filters)
	cover_days = get_cover_days(filters)

	order_uoms = get_order_uoms([row["item_code"] for row in at_risk_rows])

	items_by_supplier = defaultdict(list)
	no_supplier_count = 0

	for row in at_risk_rows:
		supplier = supplier_map.get(row["item_code"])
		if not supplier:
			no_supplier_count += 1
			continue

		stock_qty = suggest_qty(row, low_days, cover_days)
		order_qty, order_uom, conversion_factor = to_order_uom(
			stock_qty, order_uoms.get(row["item_code"]), row["stock_uom"]
		)
		items_by_supplier[supplier].append(
			{
				"item_code": row["item_code"],
				"qty": order_qty,
				"uom": order_uom,
				"conversion_factor": conversion_factor,
			}
		)

	created = [
		create_purchase_order_request(filters.get("company"), supplier, items)
		for supplier, items in items_by_supplier.items()
	]

	return {
		"created_count": len(created),
		"requests": created,
		"no_supplier_count": no_supplier_count,
		"already_requested_count": skipped_count,
	}
