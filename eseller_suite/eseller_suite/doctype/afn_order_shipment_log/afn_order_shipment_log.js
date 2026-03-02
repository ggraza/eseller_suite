// Copyright (c) 2026, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("AFN Order Shipment Log", {
	refresh(frm) {
		frm.disable_save();
		frm.disable_form();
		hanlde_retry_btn(frm);
		hanlde_fetch_order_btn(frm);
	},
});

function hanlde_retry_btn(frm) {
	if (!frm.is_new() && frm.doc.has_exceptions) {
		frm.add_custom_button('Re-try Fetching', () => {
			frm.remove_custom_button('Re-try Fetching');
			frm.set_value('exceptions',)
			frm.save();
		})
	}
}

function hanlde_fetch_order_btn(frm) {
	frappe.db.get_value('Amazon SP API Settings', { is_active: 1 }, 'name').then(r => {
		let sp_api_settings = r.message.name;
		if (sp_api_settings) {
			if (!frm.is_new() && !frm.doc.invoice_created) {
				frappe.call('eseller_suite.eseller_suite.doctype.afn_order_shipment_log.afn_order_shipment_log.check_so_existance_and_rq_job', {
					amazon_order_id: frm.doc.amazon_order_id,
					amz_setting_name: sp_api_settings
				}).then(r => {
					if (r.message) {
						frm.add_custom_button('Fetch/Update Sales Order', () => {
							frappe.call({
								method: 'eseller_suite.eseller_suite.doctype.amazon_sp_api_settings.amazon_repository.get_order',
								args: {
									amz_setting_name: sp_api_settings,
									amazon_order_ids: frm.doc.amazon_order_id
								},
								freeze: true,
								freeze_message: __("Syncing Sales Order.."),
								callback: (r) => {
									if (r && r.message) {
										frappe.show_alert({
											message: __('Sales Orders created/updated successfully'),
											indicator: 'green'
										}, 5);
										frm.reload_doc();
									}
								}
							})
						})
					}
				})
			}
		}
	})

}