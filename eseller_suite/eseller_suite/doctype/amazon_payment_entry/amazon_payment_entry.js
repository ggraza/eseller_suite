// Copyright (c) 2024, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("Amazon Payment Entry", {
	setup(frm) {
		const original_dirty = frm.dirty;
		frm.dirty = function () {
			original_dirty.apply(frm, arguments);
			// runs whenever form becomes dirty
			on_form_dirty(frm);
		};
	},
	onload(frm) {
		if (frm.is_new()) {
			frappe.db.get_single_value('eSeller Settings', 'default_mode_of_payment').then(default_mode_of_payment => {
				frm.set_value('mode_of_payment', default_mode_of_payment);
			});
		}
		frm.set_df_property('payment_details', 'cannot_add_rows', true)
	},
	refresh(frm) {
		if (frm.doc.in_progress) {
			frm.set_intro('Background syncing is in progress, Please wait and reload again', 'orange');
			frm.disable_form();
			frm.disable_save();
		}
		if (!frm.is_new() && frm.doc.docstatus === 0 && frm.doc.in_progress === 0) {
			handle_custom_buttons(frm);
		}
		if (!frm.is_new() && frm.doc.docstatus === 0) {
			set_introduction_texts(frm);
		}
		handle_realtime_updates(frm);
	},
	reset_progress(frm) {
		frm.set_value('in_progress', 0);
		frm.refresh_fields();
		frm.save();
	}
});

function on_form_dirty(frm) {
	if (frm.doc.docstatus === 0) {
		frm.enable_save();
	}
}

function handle_realtime_updates(frm) {
	frappe.realtime.on("fetch_invoice_details", (data) => {
		frappe.hide_msgprint(true);
		frappe.show_progress('Fetching Invoice Details...', data.progress, data.total, __("Fetching {0} of {1} invoices", [data.progress, data.total]), true);
		if (data.progress === data.total) {
			frm.reload_doc();
		}
	});
	frappe.realtime.on("get_missing_sales_orders", (data) => {
		frappe.hide_msgprint(true);
		frappe.show_progress('Syncing Sales Order..', data.progress, data.total, __("Fetching {0} of {1} invoices", [data.progress, data.total]), true);
		if (data.progress === data.total) {
			frm.reload_doc();
		}
	});
}

function handle_custom_buttons(frm) {
	if (!frm.is_new() && frm.doc.docstatus === 0) {
		if (!frm.doc.invoice_details_fetched) {
			frm.add_custom_button('Invoice Details', () => {
				fetch_invoice_details(frm);
			}, 'Fetch');

			frm.add_custom_button('Missing Sales Orders', async () => {
				await get_missing_sales_orders(frm);
			}, 'Fetch');

			// Button for debug purposes only for Administrator
			if (frappe.user.has_role('System Manager')) {
				frm.add_custom_button('Unset Ready to Process', () => {
					unset_ready_to_process(frm);
				}, 'Fetch');
			}
		}
	}
}

function fetch_invoice_details(frm) {
	frm.call({
		method: "fetch_invoice_details",
		doc: frm.doc,
		callback: function (r) {
			frappe.show_alert({
				message: __("Invoice Details fetched.."),
				indicator: "green",
			});
			frm.reload_doc();
		},
		freeze: true,
		freeze_message: __('Fetching Invoice Details...')
	});
}

/**
 * Function to continuously fetch missing sales orders
 * until all eligible order IDs are synced.
 */
async function get_missing_sales_orders(frm) {
	let has_more_orders = true;

	const records = await frappe.db.get_list("Amazon SP API Settings", {
		fields: ["name"],
		filters: { is_active: 1 },
	});

	const amz_setting_name = records.at(-1)?.name;

	if (!amz_setting_name) {
		frappe.msgprint("No active Amazon SP API Settings found.");
		return;
	}

	do {
		await frm.reload_doc();

		let amazon_order_ids = [];
		let count = 0;

		const max_invoice_count = await frappe.db.get_single_value(
			"eSeller Settings",
			"max_invoice_count"
		);

		for (const row of frm.doc.payment_details) {
			if (
				row.order_id &&
				row.ready_to_process == 0 &&
				row.order_id.trim() !== "" &&
				(frm.doc.consider_so_only ? row.has_sales_order == 0 : true) &&
				count < max_invoice_count &&
				!amazon_order_ids.includes(row.order_id.trim())
			) {
				amazon_order_ids.push(row.order_id.trim());
				count++;
			}
		}

		// Stop if no more orders
		if (amazon_order_ids.length === 0) {
			break;
		}

		// Process current batch
		for (let i = 0; i < amazon_order_ids.length; i++) {
			frappe.show_progress(
				"Syncing Sales Order..",
				i + 1,
				amazon_order_ids.length,
				__("Fetching {0} of {1} invoices", [
					i + 1,
					amazon_order_ids.length,
				])
			);

			try {
				await frappe.call({
					method:
						"eseller_suite.eseller_suite.doctype.amazon_sp_api_settings.amazon_repository.get_order",
					args: {
						amz_setting_name: amz_setting_name,
						amazon_order_ids: amazon_order_ids[i],
						run_si_submit_job: 0,
					},
					freeze: true,
					freeze_message: __("Syncing Sales Order.."),
				});
			} catch (err) {
				console.error("Error fetching order:", err);
			}
		}

		// Run SI submit job after processing the batch
		await frm.call({
			method: "submit_invoices_in_background",
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Fetching Invoice Details..."),
		});

		// Fetch invoice details after batch
		await frm.call({
			method: "fetch_invoice_details",
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Fetching Invoice Details..."),
		});

		await frm.reload_doc();

		// Repeat only if consider_so_only is enabled
		has_more_orders = frm.doc.consider_so_only ? true : false;

	} while (has_more_orders);

	frappe.hide_progress();

	frappe.show_alert({
		message: __("Sales order syncing completed"),
		indicator: "green",
	});

	await frm.reload_doc();
}


/**
 * function to uncheck ready to process checks in all the lines in the table
 */
function unset_ready_to_process(frm) {
	frm.call({
		method: "unset_ready_to_process",
		doc: frm.doc,
		freeze: true,
		freeze_message: __("Removing Ready to Process.."),
		callback: (r) => {
			if (r && r.message) {
				frappe.show_alert({
					message: __('Ready to Process removed successfully'),
					indicator: 'green'
				}, 5);
			}
			frm.reload_doc();
		}
	});
}

function set_introduction_texts(frm) {
	if (frm.doc.docstatus === 0) {
		frm.set_intro('');
		const total_count = frm.doc.payment_details ? frm.doc.payment_details.length : 0;
		// Get rows where checkbox is NOT checked
		const remaining_rows = (frm.doc.payment_details || []).filter(
			row => !row.ready_to_process
		);
		// Remaining unchecked rows count
		const remaining_count = remaining_rows.length;

		if (remaining_count === 0) {
			frm.set_intro('Amazon Payment Entry is ready to submit', 'green');
		}
		else {
			frm.set_intro(
				__('Please process all missing orders ({0} out of {1} remaining) before submitting.',
					[remaining_count, total_count]),
				'red'
			);
			frm.disable_save();
		}
	}
}
