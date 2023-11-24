# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, msgprint

from erpnext import get_company_currency


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns(filters)
	entries = get_entries(filters)
	item_details = get_item_details()
	data = []

	company_currency = get_company_currency(filters.get("company"))

	for d in entries:
		if d.stock_qty > 0 or filters.get("show_return_entries", 0):
			data.append(
				[
					d.name,
					d.customer,
					d.selling_price_list,
					d.territory,
				
					d.posting_date,
					d.item_code,
					d.item_name,
					item_details.get(d.item_code, {}).get("item_group"),
					item_details.get(d.item_code, {}).get("brand"),
					d.stock_qty,
					d.base_net_amount,
					d.bonus,
					d.sales_person,
					d.allocated_percentage,
					d.contribution_amt,
					company_currency,
				]
			)

	if data:
		total_row = [""] * len(data[0])
		data.append(total_row)

	return columns, data


def get_columns(filters):
	if not filters.get("doc_type"):
		msgprint(_("Please select the document type first"), raise_exception=1)

	columns = [
		{
			"label": _(filters["doc_type"]),
			"options": filters["doc_type"],
			"fieldname": frappe.scrub(filters["doc_type"]),
			"fieldtype": "Link",
			"width": 70,
		},
		{
			"label": _("Customer"),
			"options": "Customer",
			"fieldname": "customer",
			"fieldtype": "Link",
			"width": 70,
		},
		{
			"label": _("Price List"),
			"options": "Price List",
			"fieldname": "price_list",
			"fieldtype": "Link",
			"width": 70,
		},
		{
			"label": _("Territory"),
			"options": "Territory",
			"fieldname": "territory",
			"fieldtype": "Link",
			"width": 70,
		},

		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 30},
		{
			"label": _("Item Code"),
			"options": "Item",
			"fieldname": "item_code",
			"fieldtype": "Link",
			"width": 100,
		},
		{
			"label": _("Item Name"),
			"options": "Item",
			"fieldname": "item_name",
			"fieldtype": "Link",
			"width": 150,
		},
		{
			"label": _("Item Group"),
			"options": "Item Group",
			"fieldname": "item_group",
			"fieldtype": "Link",
			"width": 100,
		},
		{
			"label": _("Brand"),
			"options": "Brand",
			"fieldname": "brand",
			"fieldtype": "Link",
			"width": 20,
		},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
		{
			"label": _("Amount"),
			"options": "currency",
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 100,
		},
				{
			"label": _("Bal"),
			"fieldname": "Bonus",
			"fieldtype": "Float",
			"width": 50,
		},
		{
			"label": _("Sales Person"),
			"options": "Sales Person",
			"fieldname": "sales_person",
			"fieldtype": "Link",
			"width": 100,
		},
		{"label": _("Contribution %"), "fieldname": "contribution", "fieldtype": "Float", "width": 10,	"hidden": 1,},
		{
			"label": _("Contribution Amount"),
			"options": "currency",
			"fieldname": "contribution_amt",
			"fieldtype": "Currency",
			"width": 10,
				"hidden": 1,
		},
		{
			"label": _("Currency"),
			"options": "Currency",
			"fieldname": "currency",
			"fieldtype": "Link",
			"hidden": 1,
		},
	]

	return columns


def get_entries(filters):
	date_field = filters["doc_type"] == "Sales Order" and "transaction_date" or "posting_date"
	if filters["doc_type"] == "Sales Order":
		qty_field = "delivered_qty"
	else:
		qty_field = "qty"
	conditions, values = get_conditions(filters, date_field)

	entries = frappe.db.sql(
		"""
		SELECT
			dt.name, dt.customer, dt.territory, dt.%s as posting_date, dt_item.item_code, dt_item.item_name,
			st.sales_person, st.allocated_percentage, dt_item.warehouse,dt.selling_price_list,
		CASE
			WHEN dt.status = "Closed" THEN dt_item.%s * dt_item.conversion_factor
			ELSE dt_item.stock_qty
		END as stock_qty,
		CASE
			WHEN dt.status = "Closed" THEN (dt_item.base_net_rate * dt_item.%s * dt_item.conversion_factor)
			ELSE dt_item.base_net_amount
		END as base_net_amount,
		it_price.bonus*stock_qty as bonus,

		CASE
			WHEN dt.status = "Closed" THEN ((dt_item.base_net_rate * dt_item.%s * dt_item.conversion_factor) * st.allocated_percentage/100)
			ELSE dt_item.base_net_amount * st.allocated_percentage/100
		END as contribution_amt
		FROM
			`tab%s` dt, `tab%s Item` dt_item, `tabSales Team` st, `tabItem` it, `tabItem Price` it_price 
		WHERE
			st.parent = dt.name and dt.name = dt_item.parent and dt_item.item_code = it.item_code 
			  and st.parenttype = %s
			  and dt_item.item_code = it_price.item_code
			  and dt.selling_price_list = it_price.price_list
			  and dt_item.uom = it_price.uom
			and dt.docstatus = 1 %s order by st.sales_person, dt.name desc
		"""
		% (
			date_field,
			qty_field,
			qty_field,
			qty_field,
			filters["doc_type"],
			filters["doc_type"],
			"%s",
			conditions,
		),
		tuple([filters["doc_type"]] + values),
		as_dict=1,
	)

	return entries


def get_conditions(filters, date_field):
	conditions = [""]
	values = []

	for field in ["company", "customer", "territory"]:
		if filters.get(field):
			conditions.append("dt.{0}=%s".format(field))
			values.append(filters[field])

	if filters.get("sales_person"):
		lft, rgt = frappe.get_value("Sales Person", filters.get("sales_person"), ["lft", "rgt"])
		conditions.append(
			"exists(select name from `tabSales Person` where lft >= {0} and rgt <= {1} and name=st.sales_person)".format(
				lft, rgt
			)
		)

	if filters.get("from_date"):
		conditions.append("dt.{0}>=%s".format(date_field))
		values.append(filters["from_date"])

	if filters.get("to_date"):
		conditions.append("dt.{0}<=%s".format(date_field))
		values.append(filters["to_date"])

	items = get_items(filters)
	if items:
		conditions.append("dt_item.item_code in (%s)" % ", ".join(["%s"] * len(items)))
		values += items

	return " and ".join(conditions), values


def get_items(filters):
	if filters.get("item_group"):
		key = "item_group"
	elif filters.get("brand"):
		key = "brand"
	else:
		key = ""

	items = []
	if key:
		items = frappe.db.sql_list(
			"""select name from tabItem where %s = %s""" % (key, "%s"), (filters[key])
		)

	return items


def get_item_details():
	item_details = {}
	for d in frappe.db.sql("""SELECT `name`, `item_group`, `brand` FROM `tabItem`""", as_dict=1):
		item_details.setdefault(d.name, d)

	return item_details
