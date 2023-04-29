// Copyright (c) 2023, Alimerdan Rahimov and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Expiring items"] = {
    "filters": [
        {
            "fieldname": "item_code",
            "label": __("Item Code"),
            "fieldtype": "Link",
            "options": "Item"
        },
        {
            "fieldname": "warehouse",
            "label": __("Warehouse"),
            "fieldtype": "Link",
            "options": "Warehouse"
        },
        {
            "fieldname": "expiry_period",
            "label": __("Expiry Period (Months)"),
            "fieldtype": "Select",
            "options": ["", "1", "2", "3"]
        }
    ]
};