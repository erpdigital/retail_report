# Copyright (c) 2026, Umer and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import getdate, nowdate


class CustomerCreditSummaryReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

		if not self.filters.get("company"):
			self.filters["company"] = frappe.db.get_single_value("Global Defaults", "default_company")

	def run(self):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date must be before To Date"))

		self.get_gl_entries()

		columns = self.get_columns()
		data = self.get_data()
		return columns, data

	def get_columns(self):
		return [
			{
				"label": _("Customer"),
				"fieldtype": "Link",
				"fieldname": "party",
				"options": "Customer",
				"width": 180,
			},
			{
				"label": _("Status"),
				"fieldtype": "HTML",
				"fieldname": "status",
				"width": 100,
			},
			{
				"label": _("Color"),
				"fieldtype": "Data",
				"fieldname": "color",
				"hidden": 1,
				"width": 100,
			},
			{
				"label": _("Credit Days"),
				"fieldtype": "Data",
				"fieldname": "credit_days",
				"width": 100,
			},
			{
				"label": _("Overdue Payment"),
				"fieldname": "overdue_payment",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 140,
			},
			{
				"label": _("Closing Balance"),
				"fieldname": "closing_balance",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 140,
			},
			{
				"label": _("Currency"),
				"fieldname": "currency",
				"fieldtype": "Link",
				"options": "Currency",
				"hidden": 1,
				"width": 50,
			},
		]

	def get_data(self):
		company_currency = frappe.get_cached_value(
			"Company", self.filters.get("company"), "default_currency"
		)

		self.party_data = frappe._dict({})
		for gle in self.gl_entries:
			self.party_data.setdefault(
				gle.party,
				frappe._dict(
					{
						"party": gle.party,
						"status": "",
						"color": "#FFFFFF",
						"credit_days": "",
						"overdue_payment": 0,
						"closing_balance": 0,
						"currency": company_currency,
					}
				),
			)
			self.party_data[gle.party].closing_balance += gle.debit - gle.credit

		overdue_totals = frappe.db.sql(
			"""
			select customer, sum(outstanding_amount)
			from `tabSales Invoice`
			where status = 'Overdue' and docstatus = 1
			group by customer
			"""
		)
		overdue_totals = {row[0]: row[1] for row in overdue_totals}

		status_colors = {
			row.status: row.color
			for row in frappe.get_all("Report Settings Table", fields=["status", "color"])
		}

		all_customers = frappe.get_all("Customer", fields=["name", "payment_terms"])

		for customer in all_customers:
			party = customer.name
			if party not in self.party_data:
				continue

			status = None
			for status_value in ("Overdue", "Unpaid", "Partly Paid", "Paid"):
				status = frappe.db.get_value(
					"Sales Invoice",
					{"customer": party, "status": status_value},
					"status",
					order_by="due_date asc",
				)
				if status:
					break

			if not status:
				continue

			color = status_colors.get(status, "#FFFFFF")
			self.party_data[party].status = (
				f'<span class="span-Status" style="background-color:{color}">{status}</span>'
			)
			self.party_data[party].color = color
			self.party_data[party].credit_days = customer.payment_terms
			self.party_data[party].overdue_payment = overdue_totals.get(party, 0)

		overdue_list, unpaid_list, partial_list, paid_list = [], [], [], []
		for row in self.party_data.values():
			if not row.status:
				continue
			if "Overdue" in row.status:
				overdue_list.append(row)
			elif "Unpaid" in row.status:
				unpaid_list.append(row)
			elif "Partly Paid" in row.status:
				partial_list.append(row)
			elif "Paid" in row.status:
				paid_list.append(row)

		return overdue_list + unpaid_list + partial_list + paid_list

	def get_gl_entries(self):
		conditions = self.prepare_conditions()

		self.gl_entries = frappe.db.sql(
			"""
			select
				gle.posting_date, gle.party, gle.debit, gle.credit, gle.is_opening
			from `tabGL Entry` gle
			where
				gle.docstatus < 2 and gle.is_cancelled = 0 and gle.party_type = 'Customer'
				and ifnull(gle.party, '') != ''
				and gle.posting_date <= %(to_date)s {conditions}
			order by gle.posting_date
			""".format(
				conditions=conditions
			),
			self.filters,
			as_dict=True,
		)

	def prepare_conditions(self):
		conditions = [""]

		if self.filters.company:
			conditions.append("gle.company=%(company)s")

		if self.filters.finance_book:
			conditions.append("ifnull(finance_book,'') in (%(finance_book)s, '')")

		if self.filters.get("party"):
			conditions.append("party=%(party)s")

		if self.filters.get("customer_group"):
			lft, rgt = frappe.db.get_value(
				"Customer Group", self.filters.get("customer_group"), ["lft", "rgt"]
			)
			conditions.append(
				"""party in (select name from tabCustomer
				where exists(select name from `tabCustomer Group` where lft >= {0} and rgt <= {1}
					and name=tabCustomer.customer_group))""".format(
					lft, rgt
				)
			)

		if self.filters.get("territory"):
			lft, rgt = frappe.db.get_value("Territory", self.filters.get("territory"), ["lft", "rgt"])
			conditions.append(
				"""party in (select name from tabCustomer
				where exists(select name from `tabTerritory` where lft >= {0} and rgt <= {1}
					and name=tabCustomer.territory))""".format(
					lft, rgt
				)
			)

		if self.filters.get("payment_terms_template"):
			conditions.append(
				"party in (select name from tabCustomer where payment_terms=%(payment_terms_template)s)"
			)

		return " and ".join(conditions)


def execute(filters=None):
	return CustomerCreditSummaryReport(filters).run()
