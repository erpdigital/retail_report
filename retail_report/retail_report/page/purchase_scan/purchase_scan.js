frappe.pages['purchase_scan'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Purchase Scan'),
		single_column: true,
	});

	// The desk chrome eats roughly a third of a phone screen. Strip it back so the
	// scanner gets the full viewport, and restore it when the operator leaves.
	$('body').addClass('purchase-scan-active');

	// No maximum-scale here on purpose: pinch-zoom stays available, which matters
	// when an operator needs to read a smudged code off the screen.
	if (!document.querySelector('meta[name="viewport"]')) {
		$('head').append(
			"<meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>"
		);
	}

	// Pulled in here rather than through `app_include_js`, so the Vue bundle costs
	// nothing on the desk pages that will never show a scanner.
	frappe.require('retail_report_scan.bundle.js', () => {
		wrapper.$PurchaseScan = new frappe.RetailReport.purchase_scan(page);
	});
};

frappe.pages['purchase_scan'].on_page_hide = function () {
	$('body').removeClass('purchase-scan-active');
};
