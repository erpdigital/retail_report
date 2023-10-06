// Copyright (c) 2023, Alimerdan Rahimov and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Item Price Lists"] = {
	"filters": [
		{
			"fieldname":"item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"get_query": function() {
				return {
					"filters": {
						"is_group": 0
					}
				}
			}
		},
		{
			"fieldname": "uom",
			"label": __("Unit of Measure"),
			"fieldtype": "Link",
			"options": "UOM",
			
			"reqd": 0 // Set to 1 if you want this field to be mandatory
		}
	],
	"onload": function(report) {
		report.page.add_inner_button(__("Refresh"), function() {
			report.refresh();
		});
	}
};