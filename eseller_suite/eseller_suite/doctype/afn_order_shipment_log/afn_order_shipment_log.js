// Copyright (c) 2026, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("AFN Order Shipment Log", {
	refresh(frm) {
		frm.disable_save();
		frm.disable_form();
		hanlde_retry_btn(frm);
	},
});

function hanlde_retry_btn(frm) {
	if (!frm.is_new()) {
		frm.add_custom_button('Re-try Fetching', () => {
			frm.remove_custom_button('Re-try Fetching');
			frm.set_value('exceptions',)
			frm.save();
		})
	}
}