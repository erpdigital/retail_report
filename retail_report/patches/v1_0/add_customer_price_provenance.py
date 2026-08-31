"""Record which Purchase Invoice last moved a customer-specific Item Price.

Nothing linked a price row to the invoice that set it, so 'did this invoice change
this customer's price?' was unanswerable. These three fields make it answerable from
here on; rows written before this patch stay blank and the dialog shows them as
unknown rather than guessing.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from retail_report.api.customer_prices import is_enabled


def execute():
	# `retail_report` is installed on several sites that have no special-customer
	# workflow at all. Adding columns to Item Price there would be churn on a doctype
	# that the POS sites read constantly, for a feature they will never open.
	if not is_enabled():
		return

	create_custom_fields(
		{
			"Item Price": [
				{
					"fieldname": "custom_source_purchase_invoice",
					"label": "Set By Purchase Invoice",
					"fieldtype": "Link",
					"options": "Purchase Invoice",
					"insert_after": "price_list_rate",
					"read_only": 1,
					"description": "The Purchase Invoice whose customer-price dialog last wrote this rate.",
				},
				{
					"fieldname": "custom_source_updated_on",
					"label": "Set By Invoice On",
					"fieldtype": "Datetime",
					"insert_after": "custom_source_purchase_invoice",
					"read_only": 1,
				},
				{
					"fieldname": "custom_previous_rate",
					"label": "Previous Rate",
					"fieldtype": "Currency",
					"insert_after": "custom_source_updated_on",
					"read_only": 1,
					"description": "The rate this row held before the last invoice-driven change.",
				},
			]
		},
		ignore_validate=True,
	)
	frappe.clear_cache(doctype="Item Price")
