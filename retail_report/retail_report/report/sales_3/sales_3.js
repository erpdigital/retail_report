// Copyright (c) 2023, Alimerdan Rahimov and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Sales 3"] = {
	"filters": [
	
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -12),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		}

	],

	"formatter": function(value, row, column, data, default_formatter) {
		if (column.fieldname == "total_amount") {
			return format_currency(value, frappe.defaults.get_default("currency"));
		} else {
			return default_formatter(value, row, column, data);
		}
	},

	"onload": function(report) {
		report.page.add_inner_button(__("Refresh"), function() {
			report.refresh();
		});
	},

	"onrun": function(report) {
		report.page.set_title(__("Sales Items by Supplier"));
	}
};
