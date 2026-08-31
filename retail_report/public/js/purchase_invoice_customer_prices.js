/**
 * Adds the "Customer Prices" button to Purchase Invoice.
 *
 * `retail_report` is installed on five sites here and only the 5dogan lineage has a
 * special-customer workflow, so the button asks the server once per desk session
 * whether this site has one at all and stays hidden everywhere else.
 */

frappe.provide('frappe.RetailReport');

function feature_enabled() {
	if (!frappe.RetailReport._customer_prices_enabled) {
		frappe.RetailReport._customer_prices_enabled = frappe
			.xcall('retail_report.api.customer_prices.feature_enabled')
			.catch(() => false);
	}
	return frappe.RetailReport._customer_prices_enabled;
}

frappe.ui.form.on('Purchase Invoice', {
	refresh(frm) {
		if (frm.is_new()) return;

		feature_enabled().then((enabled) => {
			if (!enabled) return;

			frm.add_custom_button(__('Цены клиентов'), () => {
				// The bundle is pulled in on click rather than through `app_include_js`,
				// so it costs nothing on the invoices that never open it.
				frappe.require('retail_report_customer_prices.bundle.js', () => {
					frappe.RetailReport.open_customer_prices(frm);
				});
			});
		});
	},
});
