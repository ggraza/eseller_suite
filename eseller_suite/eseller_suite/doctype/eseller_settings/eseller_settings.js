// Copyright (c) 2024, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("eSeller Settings", {
	refresh(frm) {
		set_filters(frm)
		set_parent_warehouse_query(frm);
	},
	onload(frm) {
		set_parent_warehouse_query(frm);
	},
	allow_missing_warehouse_creation(frm) {
		if (frm.doc.allow_missing_warehouse_creation) {
			populate_parent_warehouses(frm);
		} else {
			clear_parent_warehouses(frm);
		}
	}
});

function set_filters(frm) {
	frm.set_query("main_warehouse", () => {
		return {
			filters: {
				"is_group": 0
			}
		};
	});
	frm.set_query("inter_company_price_list", () => {
		return {
			filters: {
				"buying": 1,
				"selling": 1,
			}
		};
	});
}

/**
 * Apply filter for parent warehouse based on company and is_group
 */
function set_parent_warehouse_query(frm) {
	if (!frm.fields_dict.parent_warehouses) return;

	frm.fields_dict.parent_warehouses.grid.get_field("default_parent_warehouse").get_query = function (doc, cdt, cdn) {
		let row = locals[cdt][cdn];
		return {
			filters: {
				company: row.company || "",
				is_group: 1
			}
		};
	};
}

/**
 * Populate parent warehouses via server call Clears parent warehouses when checkbox is unchecked
 */
function populate_parent_warehouses(frm) {
	frappe.call({
		method: "eseller_suite.eseller_suite.doctype.eseller_settings.eseller_settings.get_all_companies",
		callback: function (r) {
			if (r.message) {
				frm.clear_table("parent_warehouses");

				r.message.forEach(comp => {
					let row = frm.add_child("parent_warehouses");
					row.company = comp.name;
				});

				frm.refresh_field("parent_warehouses");
			}
		}
	});
}

/*
 * Clear table when checkbox unchecked
 */
function clear_parent_warehouses(frm) {
	frm.clear_table("parent_warehouses");
	frm.refresh_field("parent_warehouses");
}
