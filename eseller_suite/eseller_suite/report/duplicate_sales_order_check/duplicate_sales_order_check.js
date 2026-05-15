frappe.query_reports["Duplicate Sales Order Check"] = {
	onload: function (report) {
		report.delete_btn = report.page.add_inner_button(
			__("Delete Draft Duplicates"),
			async function () {
				frappe.confirm(
					__("This will delete all duplicate draft Sales Orders. Continue?"),
					async function () {

						let r = await frappe.call({
							method: "eseller_suite.eseller_suite.report.duplicate_sales_order_check.duplicate_sales_order_check.delete_all_duplicate_draft_sales_orders",
							freeze: true,
							freeze_message: __("Deleting Duplicate Draft Sales Orders...")
						});

						frappe.msgprint({
							title: __("Completed"),
							message: __("{0} Sales Orders Deleted", [r.message.deleted_count]),
							indicator: "green"
						});
						report.refresh();
					}
				);
			}
		);
	}
};