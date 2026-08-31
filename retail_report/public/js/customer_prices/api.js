const METHOD_ROOT = 'retail_report.api.customer_prices.';

/** Thin promise wrapper over frappe.call so components never touch the desk API. */
export function call(method, args = {}, { freeze = false, freeze_message = '' } = {}) {
	return new Promise((resolve, reject) => {
		frappe.call({
			method: METHOD_ROOT + method,
			args,
			freeze,
			freeze_message,
			callback: (r) => resolve(r.message),
			error: (err) => reject(err),
		});
	});
}

export const api = {
	getContext: (purchase_invoice) => call('get_context', { purchase_invoice }),
	savePrices: (purchase_invoice, changes) =>
		call(
			'save_prices',
			{ purchase_invoice, changes: JSON.stringify(changes) },
			{ freeze: true, freeze_message: __('Saving customer prices…') }
		),
};
