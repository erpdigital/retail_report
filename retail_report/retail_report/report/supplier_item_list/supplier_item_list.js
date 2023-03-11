// Copyright (c) 2023, Alimerdan Rahimov and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Supplier Item list"] = {
	"filters": [
		{
			"fieldname":"supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"reqd": 1
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.get_today(),
		}
	],
	"onload": function(report) {
		// set the title of the report
		report.page.add_inner_button(__("Set Title"), function() {
			var title = prompt("Enter Report Title");
			if (title) {
				report.page.set_title(title);
			}
		});
	},
	"onload": function(report) {
        report.page.add_inner_button(__("Stock Balance"), function() {
            var supplier = frappe.query_report.get_filter_value("supplier");
            frappe.set_route("List", "Stock Balance", {"supplier": supplier});
        }, __("View"));
    },

	"ondatarefresh": function(report) {
		// calculate the total supplied qty and stock qty
		var total_supplied_qty = 0;
		var total_stock_qty = 0;
		report.dataView.getItems().forEach(function(item) {
			total_supplied_qty += item.supplied_qty;
			total_stock_qty += item.stock_qty;
		});
		// add the total row to the report
		var total_row = {
			"supplier": __("Total"),
			"supplied_qty": total_supplied_qty,
			"stock_qty": total_stock_qty,
		};
		report.dataView.addItem(total_row);
	}
};