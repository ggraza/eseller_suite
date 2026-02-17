// Copyright (c) 2026, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("Amazon Report API Log", {
	refresh(frm) {
		frm.disable_save();
		frm.disable_form();
		handle_report_btns(frm);
	}
});

function handle_report_btns(frm) {
	if (!frm.doc.file_processed) {
		if (!frm.doc.report_document_id) {
			frm.add_custom_button('Update Report Status', () => {
				frappe.call({
					method: 'eseller_suite.eseller_suite.doctype.amazon_report_api_log.amazon_report_api_log.get_report_status',
					args: {
						report_log_id: frm.doc.name
					},
					freeze: true,
					freeze_message: __("Getting Report Status.."),
					callback: (r) => {
						frm.reload_doc();
					}
				})
			});
		}

		if (frm.doc.report_document_id) {
			frm.add_custom_button('Get Report URL', () => {
				frappe.call({
					method: 'eseller_suite.eseller_suite.doctype.amazon_report_api_log.amazon_report_api_log.get_report_url',
					args: {
						report_log_id: frm.doc.name
					},
					freeze: true,
					freeze_message: __("Getting Report URL.."),
					callback: (r) => {
						frm.reload_doc();
					}
				})
			});
		}
	}
}