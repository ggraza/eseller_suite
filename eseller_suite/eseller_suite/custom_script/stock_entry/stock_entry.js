frappe.ui.form.on('Stock Entry', {
	refresh(frm) {
		resrtict_actions_for_amazon_invoice(frm);
		set_filters(frm);
	}
})

frappe.ui.form.on('Stock Entry Detail', {
	item_code: function (frm, cdt, cdn) {
		fetch_item_details(frm, cdt, cdn);
	},
	qty: function (frm, cdt, cdn) {
		handle_bundle_items(frm, cdt, cdn);
	},
	basic_rate: function (frm, cdt, cdn) {
		handle_bundle_items(frm, cdt, cdn);
	},
	expense_account: function (frm, cdt, cdn) {
		handle_bundle_items(frm, cdt, cdn);
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
	bundle_items_add: function (frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "s_warehouse", frm.doc.from_warehouse);
		frappe.model.set_value(cdt, cdn, "t_warehouse", frm.doc.to_warehouse);
	}
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
				new_row.qty = flt(bundle_child.qty) * selected_qty;
				new_row.transfer_qty = flt(bundle_child.qty) * selected_qty;
				new_row.conversion_factor = 1;
				new_row.from_bundle_item = 1;
				new_row.uom = bundle_child.uom;
				new_row.rate = flt(row.basic_rate) ? (flt(row.basic_rate) / flt(bundle_child.qty)) : bundle_child.rate;
				new_row.basic_rate = flt(row.basic_rate) ? (flt(row.basic_rate) / flt(bundle_child.qty)) : bundle_child.rate;
				new_row.description = bundle_child.description;
				new_row.s_warehouse = row.s_warehouse;
				new_row.t_warehouse = row.t_warehouse;
				new_row.bundle_parent = row.name;
				new_row.expense_account = row.expense_account;
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
	frm.set_query("item_code", "bundle_items", function () {
		return {
			filters: {
				is_bundle_item: 1
			}
		};
	});
	frm.set_query("expense_account", "bundle_items", function () {
		return {
			filters: {
				company: frm.doc.company,
			}
		};
	});
	frm.set_query("s_warehouse", "bundle_items", function () {
		return {
			filters: {
				company: frm.doc.company,
			}
		};
	});
	frm.set_query("t_warehouse", "bundle_items", function () {
		return {
			filters: {
				company: frm.doc.company,
			}
		};
	});
}

function fetch_item_details(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (row.item_code) {
		frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "Item",
				name: row.item_code
			},
			callback: function (r) {
				if (!r.message) return;
				let item = r.message;
				frappe.model.set_value(cdt, cdn, "description", item.description);
				frappe.model.set_value(cdt, cdn, "uom", item.stock_uom);
				frappe.model.set_value(cdt, cdn, "uom", item.stock_uom);
				frappe.model.set_value(cdt, cdn, "item_name", item.item_name);
			}
		});
	}
}
