// Copyright (c) 2026, efeone and contributors
// For license information, please see license.txt

frappe.listview_settings['AFN Order Shipment Log'] = {
	onload(listview) {
		hanlde_retry_btn(listview);
		hanlde_fetch_orders_btn(listview);
	}
};

function hanlde_retry_btn(listview) {
	listview.page.add_action_item(__('Re-Try Selected'), function () {
		let selected = listview.get_checked_items();

		if (!selected.length) {
			frappe.msgprint(__('Please select at least one record.'));
			return;
		}

		let names = selected.map(doc => doc.name);

		frappe.call({
			method: "eseller_suite.eseller_suite.doctype.afn_order_shipment_log.afn_order_shipment_log.retry_fetching_selected_logs",
			args: {
				docnames: names
			},
			freeze: true,
			freeze_message: __('Processing...'),
			callback: function (r) {
				frappe.msgprint(__('Processed successfully'));
				listview.refresh();
			}
		});
	});
}

function hanlde_fetch_orders_btn(listview) {
	listview.page.add_action_item(__('Fetch Orders'), function () {
		let selected = listview.get_checked_items();

		if (!selected.length) {
			frappe.msgprint(__('Please select at least one record.'));
			return;
		}

		if (selected.length > 20) {
			frappe.msgprint(__('Maximum 20 Orders can be processed in a single try.'));
			return;
		}

		let names = selected.map(doc => doc.name);

		frappe.call({
			method: "eseller_suite.eseller_suite.doctype.afn_order_shipment_log.afn_order_shipment_log.fetch_sales_orders",
			args: {
				docnames: names
			},
			freeze: true,
			freeze_message: __('Sales orders are syncing, Please wait...'),
			callback: function (r) {
				frappe.msgprint(__('Synced successfully'));
				listview.refresh();
			}
		});
	});
}
