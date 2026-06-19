// Copyright (c) 2026, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("AFN Order Shipment Log", {
	refresh(frm) {
		$('.new-timeline .timeline-item .timeline-message-box .actions').hide();
		frm.disable_save();
		frm.disable_form();
		hanlde_retry_btn(frm);
		hanlde_fetch_order_btn(frm);
		hanlde_update_item_btn(frm);
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
				frappe.call('eseller_suite.eseller_suite.doctype.afn_order_shipment_log.afn_order_shipment_log.check_rq_job_existance', {
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
					else {
						frm.set_intro('Order syncing has been done via background jobs, Please wait!', 'orange');
					}
				})
			}
		}
	})

}

function hanlde_update_item_btn(frm) {
	if (frm.is_new() || frm.doc.has_exceptions || frm.doc.invoice_created || !frm.doc.order_created) {
		return;
	}

	frappe.call({
		method: "eseller_suite.eseller_suite.doctype.afn_order_shipment_log.afn_order_shipment_log.get_sales_order_item_codes",
		args: {
			amazon_order_id: frm.doc.amazon_order_id
		},
		callback: function (r) {
			const item_codes = r.message || [];
			if (item_codes.includes(frm.doc.item_code)) {
				// Current item already matches an item on the Sales Order, nothing to fix
				return;
			}
			frm.add_custom_button('Update Item', () => {
				update_item_popup(frm, item_codes);
			});
			frm.add_custom_button('Update Sales Order Item', () => {
				open_update_so_item_dialog(frm);
			});
		}
	});
}

function update_item_popup(frm, item_codes) {
	let d = new frappe.ui.Dialog({
		title: 'Update Item Details',
		fields: [
			{
				label: 'Item Code',
				fieldname: 'item_code',
				fieldtype: 'Link',
				options: 'Item',
				reqd: 1,
				only_select: 1,
				get_query: () => {
					return {
						filters: {
							name: ['in', item_codes]
						}
					};
				}
			},
		],
		primary_action_label: 'Update',
		primary_action(values) {
			frappe.call({
				method: "frappe.desk.form.utils.add_comment",
				args: {
					reference_doctype: frm.doctype,
					reference_name: frm.doc.name,
					content: __(`Item Code updated to ${values.item_code} by ${frappe.session.user_fullname}`),
					comment_email: frappe.session.user,
					comment_by: frappe.session.user_fullname,
				},
				callback: function (r) {
					if (!r.exc) {
						frm.set_value('item_code', values.item_code);
						frm.set_value('fc_processed', 0);
						frm.save();
						d.hide();
					}
				},
			});
		}
	});
	d.show();
}

function open_update_so_item_dialog(frm) {
	if (!frm.doc.amazon_order_id) {
		frappe.msgprint(__('Amazon Order ID is not set on this record.'));
		return;
	}

	//Find the Sales Order using amazon_order_id
	frappe.db.get_value('Sales Order', { amazon_order_id: frm.doc.amazon_order_id }, 'name').then(r => {
		const sales_order = r.message && r.message.name;

		if (!sales_order) {
			frappe.msgprint(__('No Sales Order found with Amazon Order ID: {0}', [frm.doc.amazon_order_id]));
			return;
		}

		show_dialog(frm, sales_order);
	});
}

function show_dialog(frm, sales_order) {
	const dialog = new frappe.ui.Dialog({
		title: __('Update Sales Order Item'),
		fields: [
			{
				label: __('Sales Order'),
				fieldname: 'sales_order',
				fieldtype: 'Link',
				options: 'Sales Order',
				default: sales_order,
				read_only: 1
			},
			{
				label: __('Sales Order Item'),
				fieldname: 'sales_order_item',
				fieldtype: 'Link',
				options: 'Item',
				reqd: 1,
				get_query: function () {
					return {
						query: 'eseller_suite.eseller_suite.doctype.afn_order_shipment_log.afn_order_shipment_log.get_sales_order_items',
						filters: {
							sales_order: dialog.get_value('sales_order')
						}
					};
				}
			},
			{
				label: __('New Item'),
				fieldname: 'new_item',
				fieldtype: 'Link',
				options: 'Item',
				reqd: 1,
				default: frm.doc.item_code,
				get_query: function () {
					return {
						filters: {
							is_actual_item: 1
						}
					};
				}
			}
		],
		primary_action_label: __('Update'),
		primary_action(values) {
			frappe.call({
				method: 'eseller_suite.eseller_suite.doctype.afn_order_shipment_log.afn_order_shipment_log.update_sales_order_item',
				args: {
					sales_order: values.sales_order,
					old_item_code: values.sales_order_item,
					new_item_code: values.new_item
				},
				freeze: true,
				freeze_message: __('Updating Sales Order Item...'),
				callback: function (r) {
					if (!r.exc) {
						frappe.msgprint(__('Sales Order Item updated successfully.'));
						dialog.hide();
						frm.reload_doc();
					}
				}
			});
		}
	});
	dialog.show();
}