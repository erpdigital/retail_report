import frappe
from frappe import _
from frappe.utils import execute_in_shell
import os, sys
import subprocess
@frappe.whitelist()
def get_weekly_sales_invoice_info(week_start_date):
    try:
        # Calculate the end date of the week
        week_end_date = frappe.utils.add_days(week_start_date, 6)

        # Fetch Sales Invoices for the specified week
        sales_invoices = frappe.get_all(
            'Sales Invoice',
            filters={
                'posting_date': ['between', [week_start_date, week_end_date]],
                'docstatus': 1  # To filter out canceled invoices
            },
            fields=['name', 'grand_total', 'outstanding_amount']
        )

        # Calculate whole paid and not paid amounts
        whole_paid_amount = sum(invoice['grand_total'] - invoice['outstanding_amount'] for invoice in sales_invoices)
        whole_not_paid_amount = sum(invoice['outstanding_amount'] for invoice in sales_invoices)

        return {
            'whole_paid_amount': whole_paid_amount,
            'whole_not_paid_amount': whole_not_paid_amount
        }

    except Exception as e:
        frappe.log_error(_("Error in calculating weekly sales invoice information: {0}".format(str(e))))
        frappe.throw(_("An error occurred. Please check the server logs for more details."))

@frappe.whitelist(allow_guest=True)
def restore_website(site, filename, user='alimerdan'):
    try:
        # Build the command
        command = f'bench --site {site}  restore {filename} '
       # Use subprocess to capture output and errors
        result = subprocess.run(command, shell=True, text=True, capture_output=True)

        if result.returncode == 0:
            return _('Website restore successful.')
        else:
            error_message = result.stderr if result.stderr else result.stdout
            frappe.log_error(f"Error during website restoration: {error_message}")
            return _('Website restore failed. Check logs for details.')
    except Exception as e:
        frappe.log_error(f"Exception during website restoration: {str(e)}")
        return frappe.utils.response.report_error()