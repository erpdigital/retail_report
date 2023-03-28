// Copyright (c) 2023, Alimerdan Rahimov and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Product Bundle Report"] = {
	"filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
        },
    ],

    "formatter": function (value, row, column, data, default_formatter) {
        if (column.fieldname == "product_1" || column.fieldname == "product_2") {
            return `<a href="#Form/Item/${data.item_code}" target="_blank">${value}</a>`;
        }
        else {
            return default_formatter(value, row, column, data);
        }
    },

    "onload": function (report) {
        report.page.add_inner_button(__('Export to CSV'), function () {
            report.export_report('CSV');
        });
    },

    "refresh": function (report) {
        var filters = report.get_values();
        frappe.call({
            method: "myapp.myreport.execute",
            args: filters,
            callback: function (data) {
                var columns = [
                    { "label": __("Product 1"), "fieldname": "product_1", "fieldtype": "Link", "options": "Item" },
                    { "label": __("Product 2"), "fieldname": "product_2", "fieldtype": "Link", "options": "Item" },
					{ "label": __("Number of Orders"), "fieldname": "orders", "fieldtype": "Int" },
					{ "label": __("Total Amount"), "fieldname": "total_amount", "fieldtype": "Currency" },
					];
					report.set_columns(columns);
					report.set_data(data.message);
					}
					});
					}
					};

