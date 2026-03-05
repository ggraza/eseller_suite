// Copyright (c) 2025, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("Purchase Invoice", {
	refresh(frm) {
		frm.set_query("item_code", "bundle_items", () => {
			return {
				filters: {
					is_bundle_item: 1
				}
			};
		});
		manage_custom_buttons(frm);
	}
});

frappe.ui.form.on('Purchase Invoice Item', {
	item_code: function (frm, cdt, cdn) {
		apply_bundle_items(frm, cdt, cdn);
	},
	qty: function (frm, cdt, cdn) {
		apply_bundle_items(frm, cdt, cdn);
	},
	bundle_items_remove: function (frm, cdt, cdn) {
		let deleted_row_name = cdn;
		(frm.doc.items || []).forEach(d => {
			if (d.bundle_parent === deleted_row_name) {
				frappe.model.clear_doc(d.doctype, d.name);
			}
		});
		frm.refresh_field("items");
	},
});

/*
 * When an item is selected in the bundle_items child table, fetch its bundle components and add them as child rows.
*/
function apply_bundle_items(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (row.parentfield !== "bundle_items") return;
	if (!row.item_code) return;

	frappe.call({
		method: "eseller_suite.eseller_suite.utils.get_bundle_items",
		args: {
			bundle_item: row.item_code
		},
		callback: function (r) {
			if (!r.message) return;

			let selected_qty = flt(row.qty) || 1;

			(frm.doc.items || []).forEach(d => {
				if (!d.item_code) {
					frappe.model.clear_doc(d.doctype, d.name);
				}
			});

			(frm.doc.items || []).forEach(d => {
				if (d.bundle_parent === row.name) {
					frappe.model.clear_doc(d.doctype, d.name);
				}
			});

			r.message.forEach(function (bundle_child) {
				let new_row = frm.add_child("items");
				new_row.item_code = bundle_child.item_code;
				new_row.item_name = bundle_child.item_name;
				new_row.qty = flt(bundle_child.qty) * selected_qty;
				new_row.uom = bundle_child.uom;
				new_row.rate = bundle_child.rate;
				new_row.description = bundle_child.description;
				new_row.bundle_parent = row.name;
				new_row.bundle_qty = bundle_child.qty;
				new_row.from_bundle_item = 1;
			});
			frm.refresh_field("items");
		}
	});
}

function manage_custom_buttons(frm) {
	if (frm.doc.amazon_invoice_id) {
			if (frm.doc.inter_company_invoice_reference) {
				frm.add_custom_button(__('Inter-Company Sales Invoice'), () => {
					frappe.set_route('Form', 'Sales Invoice', frm.doc.inter_company_invoice_reference);
				}, __('View'));
			}
	}
}
