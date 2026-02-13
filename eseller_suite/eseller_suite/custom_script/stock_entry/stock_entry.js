frappe.ui.form.on('Stock Entry', {
	refresh(frm) {
		resrtict_actions_for_amazon_invoice(frm);
	}
})

function resrtict_actions_for_amazon_invoice(frm) {
	if (frm.doc.amazon_invoice_id) {
		frm.disable_form();
		frm.disable_save();
		frm.clear_custom_buttons();
	}
}