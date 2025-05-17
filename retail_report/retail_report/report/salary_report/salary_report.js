frappe.query_reports["Salary Report"] = {
     onload: function(report) {
        report.page.add_inner_button(__("Pay Payroll"), () => {
            frappe.prompt([
                {
                    label: "Дата выплаты",
                    fieldname: "payment_date",
                    fieldtype: "Date",
                    default: frappe.datetime.get_today(),
                    reqd: 1
                }
            ], (values) => {
                frappe.call({
                    method: "create_payroll",
                    args: {
                        from_date: report.get_filter_value("from_date"),
                        to_date: report.get_filter_value("to_date"),
                        payment_date: values.payment_date
                    },
                    callback: function(r) {
                        frappe.msgprint(__("Выплаты произведены."));
                    }
                });
            }, __("Выплата зарплаты"));
        });
    },
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
    
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
     
            "reqd": 1
        }
    ]
};
