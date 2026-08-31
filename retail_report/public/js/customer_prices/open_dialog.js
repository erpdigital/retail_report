import CustomerPrices from './CustomerPrices.vue';

frappe.provide('frappe.RetailReport');

/**
 * Open the customer-price grid over a Purchase Invoice.
 *
 * Deliberately a modal rather than a page: the operator is in the middle of pricing a
 * delivery, and the thing this replaces navigated them away to the Item Price list to
 * do the edit, abandoning the invoice.
 */
frappe.RetailReport.open_customer_prices = function (frm) {
	const dialog = new frappe.ui.Dialog({
		title: __('Customer Prices — {0}', [frm.doc.name]),
		size: 'extra-large',
		fields: [{ fieldtype: 'HTML', fieldname: 'grid' }],
		primary_action_label: __('Save Prices'),
		primary_action: async () => {
			const res = await dialog.$cp.save();
			// Left open on a no-op save so the operator does not lose their place; a real
			// save has already refreshed the grid underneath them.
			if (res) dialog.hide();
		},
		secondary_action_label: __('Close'),
		secondary_action: () => dialog.hide(),
	});

	const $mount = $('<div></div>');
	dialog.get_field('grid').$wrapper.append($mount);

	dialog.$vue = new Vue({
		el: $mount[0],
		render: (h) => h(CustomerPrices, { props: { purchaseInvoice: frm.doc.name } }),
	});
	dialog.$cp = dialog.$vue.$children[0];

	dialog.onhide = () => {
		if (dialog.$vue) dialog.$vue.$destroy();
	};

	dialog.show();
	return dialog;
};
