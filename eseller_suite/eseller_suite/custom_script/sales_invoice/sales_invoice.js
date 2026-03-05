// Copyright (c) 2025, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		manage_custom_buttons(frm);
	}
});

function manage_custom_buttons(frm) {
    if (frm.doc.amazon_invoice_id) {
			if (frm.doc.inter_company_invoice_reference) {
				frm.add_custom_button(__('Inter-Company Purchase Invoice'), () => {
					frappe.set_route('Form', 'Purchase Invoice', frm.doc.inter_company_invoice_reference);
				}, __('View'));
			}
	}
}
