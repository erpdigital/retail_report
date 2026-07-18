// Copyright (c) 2026, Alimerdan Rahimov and contributors
// For license information, please see license.txt

frappe.ui.form.on("Purchase Order Request", {
	refresh: function (frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status !== "Ordered") {
			frm.add_custom_button(
				__("Purchase Order"),
				function () {
					frappe.model.open_mapped_doc({
						method:
							"retail_report.retail_report.doctype.purchase_order_request.purchase_order_request.make_purchase_order",
						frm: frm,
					});
				},
				__("Create")
			);
		}
	},
});

function update_row_weight(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	row.total_weight = flt(row.qty) * flt(row.weight_per_unit);
	refresh_field("total_weight", cdn, "items");
	update_totals(frm);
}

function update_totals(frm) {
	let total_qty = 0;
	let total_weight = 0;

	(frm.doc.items || []).forEach(function (row) {
		total_qty += flt(row.qty);
		total_weight += flt(row.total_weight);
	});

	frm.set_value("total_qty", total_qty);
	frm.set_value("total_weight", total_weight);
}

frappe.ui.form.on("Purchase Order Request Item", {
	qty: function (frm, cdt, cdn) {
		update_row_weight(frm, cdt, cdn);
	},
	item_code: function (frm, cdt, cdn) {
		update_row_weight(frm, cdt, cdn);
	},
});
