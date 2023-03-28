frappe.query_reports["ABC Analyse"] = {
    "filters": [
        // Add filters if necessary
    ],
    "formatter": function(row, cell, value, columnDef, dataContext, default_formatter) {
        // Add formatting if necessary
        return default_formatter(row, cell, value, columnDef, dataContext);
    }
};