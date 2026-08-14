const METHOD_ROOT = 'retail_report.api.purchase_scan.';

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
	getDefaults: () => call('get_defaults'),
	scanLookup: (code) => call('scan_lookup', { code }),
	searchItems: (query) => call('search_items', { query }),
	createItem: (payload) => call('create_item', payload, { freeze: true, freeze_message: __('Creating item…') }),
	saveSession: (doc) => call('save_session', { doc: JSON.stringify(doc) }),
	createInvoice: (name) =>
		call('create_invoice', { name }, { freeze: true, freeze_message: __('Creating Purchase Invoice…') }),
};

/** Link-field search against any doctype, for the supplier/warehouse pickers. */
export function searchLink(doctype, txt, filters = {}) {
	return new Promise((resolve) => {
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype,
				filters,
				or_filters: txt ? [['name', 'like', `%${txt}%`]] : undefined,
				fields: ['name'],
				limit_page_length: 20,
				order_by: 'name asc',
			},
			callback: (r) => resolve((r.message || []).map((d) => d.name)),
		});
	});
}
