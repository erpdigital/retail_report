import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
	create_custom_fields(
		{
			"Supplier": [
				{
					"fieldname": "exclude_from_reorder_suggestions",
					"label": "Exclude from Reorder Suggestions",
					"fieldtype": "Check",
					"insert_after": "disabled",
					"default": "0",
					"description": (
						"When checked, this supplier is skipped by the Stock Cover Forecast "
						"report's 'Create Purchase Requests' workflow - items last bought from "
						"them are routed to their next most recent non-excluded supplier instead."
					),
				}
			]
		}
	)
	frappe.clear_cache(doctype="Supplier")
