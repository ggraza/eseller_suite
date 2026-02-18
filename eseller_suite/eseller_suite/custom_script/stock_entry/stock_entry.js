frappe.ui.form.on('Stock Entry', {
	refresh(frm) {
		resrtict_actions_for_amazon_invoice(frm);
		set_filters(frm);
	}
})

frappe.ui.form.on('Stock Entry Detail', {
	item_code: function(frm, cdt, cdn) {
		handle_bundle_items(frm, cdt, cdn);
	},
	qty: function(frm, cdt, cdn) {
		handle_bundle_items(frm, cdt, cdn);
	},
	bundle_items_remove: function(frm, cdt, cdn) {
		let deleted_row_name = cdn;
		(frm.doc.items || []).forEach(d => {
			if (d.bundle_parent === deleted_row_name) {
				frappe.model.clear_doc(d.doctype, d.name);
			}
		});
		frm.refresh_field("items");
	},

});

/**
 * Expands a bundle item into its component items in the Stock Entry.
 *
 * Fetches bundle components, removes previously linked rows,
 * recalculates quantities based on selected bundle qty,
 * and inserts updated component rows into the `items` table.
 */
function handle_bundle_items(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (row.parentfield !== "bundle_items") return;
	if (!row.item_code) return;

	frappe.call({
		method: "eseller_suite.eseller_suite.custom_script.stock_entry.stock_entry.get_bundle_items",
		args: {
			bundle_item: row.item_code
		},
		callback: function(r) {
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
			r.message.forEach(function(bundle_child) {
				let new_row = frm.add_child("items");
				new_row.item_code = bundle_child.item_code;
				new_row.qty = flt(bundle_child.qty) * selected_qty;
				new_row.uom = bundle_child.uom;
				new_row.rate = bundle_child.rate;
				new_row.description = bundle_child.description;
				new_row.bundle_parent = row.name;
			});
			frm.refresh_field("items");
		}
	});
}

function resrtict_actions_for_amazon_invoice(frm) {
	if (frm.doc.amazon_invoice_id) {
		frm.disable_form();
		frm.disable_save();
		frm.clear_custom_buttons();
	}
}

/*
* Function to apply filters in the item_code field in Bundle Items child table
 */
function set_filters(frm) {
	frm.set_query("item_code", "bundle_items", function() {
		return {
			filters: {
				is_bundle_item: 1
			}
		};
	});
}