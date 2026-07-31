// Copyright (c) 2026, and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Cover Forecast"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
		},
		{
			"fieldname": "from_date",
			"label": __("Sales History From"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -6),
		},
		{
			"fieldname": "to_date",
			"label": __("Sales History To"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
		},
		{
			"fieldname": "item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
		},
		{
			"fieldname": "item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"get_query": function () {
				return {
					query: "erpnext.controllers.queries.item_query",
				};
			},
		},
		{
			"fieldname": "critical_days",
			"label": __("Critical Threshold (Days)"),
			"fieldtype": "Float",
			"default": 1,
		},
		{
			"fieldname": "low_days",
			"label": __("Low Stock Threshold (Days)"),
			"fieldtype": "Float",
			"default": 5,
		},
	],

	onload: function (report) {
		report.page.add_inner_button(__("Create Purchase Requests"), function () {
			stock_cover_forecast.show_supplier_dialog(report);
		});
	},
};

const stock_cover_forecast = {
	method_path: "retail_report.retail_report.report.stock_cover_forecast.stock_cover_forecast",
	NO_SUPPLIER_KEY: "No Supplier History",

	// The backend always sends/receives the raw (untranslated) key so comparisons
	// stay stable regardless of UI language - only the on-screen label is translated.
	display_supplier: function (supplier) {
		return supplier === this.NO_SUPPLIER_KEY ? __(this.NO_SUPPLIER_KEY) : supplier;
	},

	show_supplier_dialog: function (report) {
		const filters = report.get_values();

		frappe.call({
			method: `${this.method_path}.get_at_risk_suppliers`,
			args: { filters },
			freeze: true,
			callback: (r) => {
				const suppliers = (r.message && r.message.suppliers) || [];
				const skipped_count = (r.message && r.message.skipped_count) || 0;

				if (!suppliers.length) {
					frappe.msgprint(
						skipped_count
							? __(
									"No red or yellow items left to request - {0} item(s) already have an open Purchase Order Request.",
									[skipped_count]
							  )
							: __("No red or yellow items found for the current filters.")
					);
					return;
				}

				const note_html = skipped_count
					? `<div class="text-muted" style="padding:0 14px 8px;">
						${__("{0} item(s) already have an open Purchase Order Request and were left out below.", [skipped_count])}
					</div>`
					: "";

				const rows_html = suppliers
					.map((s) => {
						const is_unknown = s.supplier === stock_cover_forecast.NO_SUPPLIER_KEY;
						const bg = is_unknown ? "background-color:var(--yellow-50, #fff8e6);" : "";
						const badges = `
							${s.critical_count ? `<span style="color:#fff;background:#ff0000;border-radius:3px;padding:1px 6px;margin-right:4px;">${s.critical_count} ${__("critical")}</span>` : ""}
							${s.low_count ? `<span style="color:#000;background:#f9ff4f;border-radius:3px;padding:1px 6px;">${s.low_count} ${__("low")}</span>` : ""}
						`;
						const subtext = is_unknown
							? `<div class="text-muted" style="font-size:11px;">${__("No purchase history - you'll need to set a supplier manually")}</div>`
							: "";

						return `
						<div class="scf-supplier-row" data-supplier="${frappe.utils.escape_html(s.supplier)}"
							style="display:flex;justify-content:space-between;align-items:center;
								padding:10px 14px;border-bottom:1px solid var(--border-color);cursor:pointer;${bg}">
							<div>
								<span>${frappe.utils.escape_html(stock_cover_forecast.display_supplier(s.supplier))}</span>
								${subtext}
							</div>
							<div>${badges}</div>
						</div>`;
					})
					.join("");

				const dialog = new frappe.ui.Dialog({
					title: __("Suppliers with Low/Critical Stock Items"),
					size: "large",
					fields: [
						{
							fieldname: "list_html",
							fieldtype: "HTML",
							options: `${note_html}<div style="max-height:420px;overflow-y:auto;">${rows_html}</div>`,
						},
					],
					primary_action_label: __("Create Requests for All Suppliers"),
					primary_action: () => {
						frappe.confirm(
							__(
								"This creates one draft Purchase Order Request per supplier below, using the suggested quantities as-is (no per-item review). Items with no supplier history will be skipped. Continue?"
							),
							() => {
								dialog.hide();
								stock_cover_forecast.bulk_create(report, filters);
							}
						);
					},
				});

				dialog.$wrapper.find(".scf-supplier-row").on("click", function () {
					const supplier = $(this).attr("data-supplier");
					dialog.hide();
					stock_cover_forecast.show_item_dialog(report, filters, supplier);
				});

				dialog.show();
			},
		});
	},

	bulk_create: function (report, filters) {
		frappe.call({
			method: `${this.method_path}.create_purchase_order_requests_for_all_suppliers`,
			args: { filters },
			freeze: true,
			freeze_message: __("Creating Purchase Order Requests..."),
			callback: (r) => {
				const res = r.message || {};
				const lines = [__("Created {0} Purchase Order Request(s), one per supplier.", [res.created_count || 0])];

				if (res.no_supplier_count) {
					lines.push(__("{0} item(s) had no supplier history and were skipped.", [res.no_supplier_count]));
				}

				frappe.msgprint(lines.join("<br>"));
			},
		});
	},

	show_item_dialog: function (report, filters, supplier) {
		frappe.call({
			method: `${this.method_path}.get_at_risk_items_for_supplier`,
			args: { filters, supplier },
			freeze: true,
			callback: (r) => {
				const items = r.message || [];

				if (!items.length) {
					frappe.msgprint(__("No items found for {0}", [stock_cover_forecast.display_supplier(supplier)]));
					return;
				}

				const rows_html = items
					.map((item) => {
						const xyz_warning = item.xyz_category === "Z";
						const xyz_html = xyz_warning
							? `<span class="text-danger" title="${__(
									"Erratic/insufficient demand history - the suggested qty is less reliable for this item"
							  )}">${item.xyz_category} ⚠</span>`
							: item.xyz_category;
						const stock_html = item.negative_stock
							? `<span class="text-danger" title="${__(
									"Negative stock - likely a data issue, verify before ordering"
							  )}">${item.current_stock} ⚠</span>`
							: item.current_stock;

						return `
						<tr data-item-code="${frappe.utils.escape_html(item.item_code)}">
							<td><input type="checkbox" class="scf-item-check" checked></td>
							<td>${frappe.utils.escape_html(item.item_code)}</td>
							<td>${frappe.utils.escape_html(item.item_name || "")}</td>
							<td class="text-center">${frappe.utils.escape_html(item.abc_category || "")}</td>
							<td class="text-center">${xyz_html}</td>
							<td class="text-right">${stock_html}</td>
							<td>${frappe.utils.escape_html(item.stock_uom || "")}</td>
							<td>
								<input type="number" class="form-control scf-item-qty"
									value="${item.suggested_qty}" min="0" step="any" style="width:100px;">
							</td>
						</tr>`;
					})
					.join("");

				const table_html = `
					<div style="max-height:420px;overflow-y:auto;">
					<table class="table table-bordered" style="margin-bottom:0;">
						<thead>
							<tr>
								<th style="width:36px;"><input type="checkbox" class="scf-select-all" checked></th>
								<th>${__("Item")}</th>
								<th>${__("Item Name")}</th>
								<th>${__("ABC")}</th>
								<th>${__("XYZ")}</th>
								<th class="text-right">${__("Current Stock")}</th>
								<th>${__("UOM")}</th>
								<th>${__("Qty to Order")}</th>
							</tr>
						</thead>
						<tbody>${rows_html}</tbody>
					</table>
					</div>
					<div class="text-muted" style="padding-top:6px;font-size:12px;">
						${__("⚠ flags erratic (Z) demand history or negative stock - double check those before ordering.")}
					</div>`;

				const dialog = new frappe.ui.Dialog({
					title: __("Items to Request from {0}", [stock_cover_forecast.display_supplier(supplier)]),
					size: "large",
					fields: [{ fieldname: "items_html", fieldtype: "HTML", options: table_html }],
					primary_action_label: __("Create Purchase Order Request"),
					primary_action: () => {
						const rows = [];
						dialog.$wrapper.find("tbody tr").each(function () {
							const $row = $(this);
							if ($row.find(".scf-item-check").is(":checked")) {
								rows.push({
									item_code: $row.attr("data-item-code"),
									qty: flt($row.find(".scf-item-qty").val()),
								});
							}
						});

						if (!rows.length) {
							frappe.msgprint(__("Select at least one item"));
							return;
						}

						frappe.call({
							method: `${this.method_path}.create_purchase_order_request`,
							args: {
								company: filters.company,
								supplier: supplier,
								items: rows,
							},
							freeze: true,
							callback: (res) => {
								dialog.hide();
								frappe.show_alert({
									message: __('Purchase Order Request <a href="/app/purchase-order-request/{0}">{0}</a> created', [
										res.message,
									]),
									indicator: "green",
								});
								// Stay in the flow instead of navigating away - re-fetch so the
								// just-requested items (now excluded by the duplicate-order guard)
								// drop out, and the analyst can move straight to the next supplier.
								stock_cover_forecast.show_supplier_dialog(report);
							},
						});
					},
				});

				dialog.$wrapper.find(".scf-select-all").on("change", function () {
					dialog.$wrapper.find(".scf-item-check").prop("checked", $(this).is(":checked"));
				});

				dialog.show();
			},
		});
	},
};
