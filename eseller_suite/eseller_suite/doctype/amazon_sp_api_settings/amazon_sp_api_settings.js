// Copyright (c) 2024, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on('Amazon SP API Settings', {
	refresh(frm) {
		set_filters(frm);
		hanlde_retry_btn(frm);
		handle_report_btn(frm);
	},
});

function set_filters(frm) {
	frm.set_query("warehouse", () => {
		return {
			filters: {
				"is_group": 0,
				"company": frm.doc.company,
			}
		};
	});
	frm.set_query("afn_warehouse", () => {
		return {
			filters: {
				"is_group": 0,
				"company": frm.doc.company,
			}
		};
	});
	frm.set_query("temporary_order_warehouse", () => {
		return {
			filters: {
				"is_group": 0,
				"company": frm.doc.company,
			}
		};
	});
	frm.set_query("market_place_account_group", () => {
		return {
			filters: {
				"is_group": 1,
				"company": frm.doc.company,
			}
		};
	});
	frm.set_query("mfn_postage_fee_account_head", () => {
		return {
			filters: {
				"is_group": 0,
				"company": frm.doc.company,
			}
		};
	});
}

function hanlde_retry_btn(frm) {
	frm.add_custom_button('Get Order', () => {
		let d = new frappe.ui.Dialog({
			title: 'Sync by Order ID',
			fields: [
				{
					label: 'Amazon Order ID',
					fieldname: 'amazon_order_id',
					fieldtype: 'Data',
					reqd: 1,
				},
			],
			primary_action_label: 'Sync',
			primary_action(values) {
				d.hide();
				frappe.call({
					method: 'eseller_suite.eseller_suite.doctype.amazon_sp_api_settings.amazon_repository.get_order',
					args: {
						amz_setting_name: frm.doc.name,
						amazon_order_ids: values.amazon_order_id
					},
					freeze: true,
					freeze_message: __("Syncing Sales Order.."),
					callback: (r) => {
						if (r && r.message) {
							frappe.show_alert({
								message: __('Sales Orders created/updated successfully'),
								indicator: 'green'
							}, 5);
						}
					}
				})
			}
		});
		d.show();
	})

	frm.add_custom_button('Get Orders', () => {
		let d = new frappe.ui.Dialog({
			title: 'Sync by Order ID',
			fields: [
				{
					label: 'Amazon Order IDs',
					fieldname: 'amazon_order_ids',
					fieldtype: 'Small Text',
					reqd: 1,
				},
			],
			primary_action_label: 'Sync',
			primary_action(values) {
				d.hide();
				// list object with new line seperation;
				// let amazon_order_ids = values.amazon_order_ids.split(/\r?\n/).map(id => id.trim()).filter(id => id.length > 0).join(",");
				// String object with , seperated values
				let amazon_order_ids = values.amazon_order_ids.split(/\r?\n/).map(id => id.trim()).filter(id => id.length > 0).join(",");
				frappe.call({
					method: 'eseller_suite.eseller_suite.doctype.amazon_sp_api_settings.amazon_repository.get_orders',
					args: {
						last_updated_after: frappe.datetime.get_today(),
						amz_setting_name: frm.doc.name,
						amazon_order_ids: amazon_order_ids
					},
					freeze: true,
					freeze_message: __("Syncing Sales Order.."),
					callback: (r) => {
						if (r && r.message) {
							frappe.show_alert({
								message: __('Sales Orders created/updated successfully'),
								indicator: 'green'
							}, 5);
						}
					}
				})
			}
		});
		d.show();
	});
}

function handle_report_btn(frm) {
	frm.add_custom_button('Get Report', () => {
		let d = new frappe.ui.Dialog({
			title: 'Sync by Order ID',
			fields: [
				{
					label: 'Report Type',
					fieldname: 'report_type',
					fieldtype: 'Link',
					options: 'Amazon Report Type',
					reqd: 1,
				},
				{
					label: 'From Date',
					fieldname: 'from_date',
					fieldtype: 'Date',
					default: frappe.datetime.add_days(frappe.datetime.get_today(), -1),
					reqd: 1,
				},
				{
					label: 'To Date',
					fieldname: 'to_date',
					fieldtype: 'Date',
					default: frappe.datetime.get_today(),
					reqd: 1,
				}
			],
			primary_action_label: 'Sync',
			primary_action(values) {
				d.hide();
				frappe.call({
					method: 'create_report',
					doc: frm.doc,
					args: {
						report_type: values.report_type,
						from_date: values.from_date,
						to_date: values.to_date
					},
					freeze: true,
					freeze_message: __("Creating Reports.."),
					callback: (r) => {
						if (r && r.message) {
							frappe.show_alert({
								message: __('Report created successfully.'),
								indicator: 'green'
							}, 5);
						}
					}
				})
			}
		});
		d.show();
	})
}
