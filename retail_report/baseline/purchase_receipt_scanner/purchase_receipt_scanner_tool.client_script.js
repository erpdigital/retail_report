
frappe.ui.form.on("Purchase Receipt Scanner", {
    onload: (frm) => {
        if (!frm.doc.date) frm.set_value("date", frappe.datetime.get_today());
    },
    refresh: (frm) => {
        prs_focus_scan(frm);
        if (frm.doc.purchase_invoice) {
            frm.set_intro(__("Purchase Invoice {0} has already been created from this scan.",
                [`<a href="/app/purchase-invoice/${frm.doc.purchase_invoice}">${frm.doc.purchase_invoice}</a>`]), "green");
        } else if (!frm.is_new()) {
            frm.add_custom_button(__("Create Purchase Invoice"),
                () => prs_create_purchase_invoice(frm)).addClass("btn-primary");
        }
    },
    scan_barcode: (frm) => {
        const code = (frm.doc.scan_barcode || "").trim();
        if (!code) return;
        frm.set_value("scan_barcode", "");
        prs_lookup_item(frm, code);
    },
    select_item: (frm) => {
        const item_code = frm.doc.select_item;
        if (!item_code) return;
        frm.set_value("select_item", "");
        prs_qty_dialog(frm, item_code, "", null);
    },
    create_item_btn: (frm) => {
        prs_new_item_dialog(frm, null);
    },
});

function prs_focus_scan(frm) {
    setTimeout(() => {
        const f = frm.get_field("scan_barcode");
        if (f && f.$input) f.$input.focus();
    }, 300);
}

function prs_lookup_item(frm, code) {
    frappe.db.get_value("Item Barcode", { barcode: code }, ["parent", "uom"], null, "Item").then((r) => {
        const d = r && r.message;
        if (d && d.parent) {
            prs_qty_dialog(frm, d.parent, code, d.uom);
        } else {
            frappe.db.exists("Item", code).then((exists) => {
                if (exists) prs_qty_dialog(frm, code, code, null);
                else prs_new_item_dialog(frm, code);
            });
        }
    });
}

function prs_qty_dialog(frm, item_code, barcode, scanned_uom) {
    frappe.call({ method: "frappe.client.get", args: { doctype: "Item", name: item_code } }).then((r) => {
        const item = r.message;
        let uoms = [item.stock_uom];
        (item.uoms || []).forEach((u) => { if (u.uom && !uoms.includes(u.uom)) uoms.push(u.uom); });
        const d = new frappe.ui.Dialog({
            title: __("Add Item"),
            fields: [
                { fieldtype: "HTML", options:
                    `<div style="font-size:16px;font-weight:bold;margin-bottom:4px;">${frappe.utils.escape_html(item.item_name || item.name)}</div>
                     <div class="text-muted" style="margin-bottom:10px;">${frappe.utils.escape_html(item.name)}</div>` },
                { fieldname: "qty", fieldtype: "Float", label: __("Quantity"), reqd: 1, default: 1 },
                { fieldname: "uom", fieldtype: "Select", label: __("Unit of Measure"),
                  options: uoms.join("\n"), reqd: 1, default: scanned_uom || item.stock_uom },
            ],
            primary_action_label: __("Add"),
            primary_action: (values) => {
                d.hide();
                prs_add_row(frm, { barcode: barcode, item_code: item.name, item_name: item.item_name,
                    qty: values.qty, uom: values.uom, is_new_item: 0 });
            },
        });
        d.show();
        setTimeout(() => { const q = d.get_field("qty"); if (q && q.$input) q.$input.select(); }, 400);
        d.$wrapper.on("hidden.bs.modal", () => prs_focus_scan(frm));
    });
}

function prs_new_item_dialog(frm, barcode) {
    const dialog_fields = [];
    if (barcode) {
        dialog_fields.push({ fieldtype: "HTML", options:
            `<div class="alert alert-warning">${__("Barcode {0} was not found in stock. A new item will be created.",
                [`<b>${frappe.utils.escape_html(barcode)}</b>`])}</div>` });
    }
    dialog_fields.push({ fieldname: "item_name", fieldtype: "Data",
        label: __("Item Name (saved as NEW_01 + name)"), reqd: 1 });
    if (!barcode) {
        dialog_fields.push({ fieldname: "item_code", fieldtype: "Data",
            label: __("Item Code (optional — generated automatically if empty)") });
    }
    dialog_fields.push({ fieldname: "uom", fieldtype: "Link", options: "UOM",
        label: __("Unit of Measure"), reqd: 1, default: "шт" });
    dialog_fields.push({ fieldname: "qty", fieldtype: "Float", label: __("Quantity"), reqd: 1, default: 1 });

    const d = new frappe.ui.Dialog({
        title: barcode ? __("Item not found — Create New Item") : __("Create New Item (no barcode)"),
        fields: dialog_fields,
        primary_action_label: __("Create & Add"),
        primary_action: (values) => {
            const full_name = "NEW_01 " + values.item_name.trim();
            const item_code = barcode || (values.item_code || "").trim()
                || ("NB-" + Date.now().toString(36).toUpperCase());
            const doc = {
                doctype: "Item",
                item_code: item_code,
                item_name: full_name,
                item_group: "NEW_ITEMS",
                stock_uom: values.uom,
                is_stock_item: 1,
                is_purchase_item: 1,
            };
            if (barcode) doc.barcodes = [{ barcode: barcode }];
            frappe.call({
                method: "frappe.client.insert",
                args: { doc: doc },
                freeze: true,
                freeze_message: __("Creating Item..."),
            }).then((r) => {
                d.hide();
                frappe.show_alert({ message: __("Item {0} created", [r.message.name]), indicator: "green" });
                prs_add_row(frm, { barcode: barcode || "", item_code: r.message.name, item_name: full_name,
                    qty: values.qty, uom: values.uom, is_new_item: 1 });
            });
        },
    });
    d.show();
    setTimeout(() => { const f = d.get_field("item_name"); if (f && f.$input) f.$input.focus(); }, 400);
    d.$wrapper.on("hidden.bs.modal", () => prs_focus_scan(frm));
}

function prs_add_row(frm, data) {
    const existing = (frm.doc.items || []).find((row) => row.item_code === data.item_code && row.uom === data.uom);
    if (existing) {
        frappe.model.set_value(existing.doctype, existing.name, "qty", (existing.qty || 0) + data.qty);
    } else {
        frm.add_child("items", data);
        frm.refresh_field("items");
    }
    if (frm.doc.supplier && frm.doc.warehouse) {
        frm.save();
    }
    prs_focus_scan(frm);
}

function prs_create_purchase_invoice(frm) {
    if (!(frm.doc.items || []).length) {
        frappe.msgprint(__("No items scanned."));
        return;
    }
    const proceed = () => {
        const codes = [...new Set(frm.doc.items.map((r) => r.item_code))];
        frappe.call({
            method: "frappe.client.get_list",
            args: { doctype: "Item", filters: [["name", "in", codes]],
                fields: ["name", "item_name"], limit_page_length: 0 },
        }).then((r) => {
            const bad = (r.message || []).filter((i) => (i.item_name || "").toUpperCase().startsWith("NEW_"));
            if (bad.length) {
                const rows = bad.map((i) =>
                    `<li><a href="/app/item/${encodeURIComponent(i.name)}" target="_blank">${frappe.utils.escape_html(i.item_name)}</a> (${frappe.utils.escape_html(i.name)})</li>`).join("");
                frappe.msgprint({
                    title: __("New items need master data"),
                    indicator: "orange",
                    message: __("These items still have temporary NEW_ names. Open each item, set the real name and units of measure, then try again:") + `<ul>${rows}</ul>`,
                });
                return;
            }
            prs_insert_pi(frm);
        });
    };
    if (frm.is_dirty() || frm.is_new()) { frm.save().then(proceed); } else { proceed(); }
}

function prs_insert_pi(frm) {
    Promise.all(frm.doc.items.map((row) =>
        frappe.call({
            method: "erpnext.stock.get_item_details.get_conversion_factor",
            args: { item_code: row.item_code, uom: row.uom },
        }).then((r) => ({
            item_code: row.item_code,
            qty: row.qty,
            uom: row.uom,
            conversion_factor: (r.message && r.message.conversion_factor) || 1,
            warehouse: frm.doc.warehouse,
        }))
    )).then((items) => {
        frappe.call({
            method: "frappe.client.insert",
            args: { doc: {
                doctype: "Purchase Invoice",
                company: frappe.defaults.get_user_default("Company") || frappe.defaults.get_global_default("company"),
                supplier: frm.doc.supplier,
                posting_date: frm.doc.date,
                update_stock: 1,
                set_warehouse: frm.doc.warehouse,
                items: items,
            } },
            freeze: true,
            freeze_message: __("Creating Purchase Invoice..."),
        }).then((r) => {
            frm.set_value("purchase_invoice", r.message.name);
            frm.save().then(() => {
                frappe.show_alert({ message: __("Purchase Invoice {0} created", [r.message.name]), indicator: "green" });
                frappe.set_route("Form", "Purchase Invoice", r.message.name);
            });
        });
    });
}
