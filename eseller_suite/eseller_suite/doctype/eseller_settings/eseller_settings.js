// Copyright (c) 2024, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("eSeller Settings", {
	refresh(frm) {
		set_parent_warehouse_query(frm);
	},
	onload(frm) {
		set_parent_warehouse_query(frm);
	}
});

function set_parent_warehouse_query(frm) {
	frm.fields_dict.parent_warehouses.grid.get_field("default_parent_warehouse").get_query =
		function (doc, cdt, cdn) {
			let row = locals[cdt][cdn];
			return {
				filters: {
					company: row.company || "",
					is_group: 1
				}
			};
		};
}
