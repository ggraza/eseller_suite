// Copyright (c) 2026, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("Amazon STN Entry", {
	stn_file(frm) {
		if (!frm.doc.stn_file) {
			frm.clear_table("stn_entries");
			frm.refresh_field("stn_entries");
		}
	}
});

