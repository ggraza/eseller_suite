import frappe

def execute():
	settings = {
		"Selling Settings": {
			"allow_multiple_items": 1,
			"editable_bundle_item_rates": 0,
			"so_required": "No",
			"dn_required": "No",
		},
		"Accounts Settings": {
			"delete_linked_ledger_entries": 1,
		},
		"Buying Settings": {
			"po_required": "No",
			"pr_required": "No",
			"allow_multiple_items": 1,
		},
	}

	for doctype, values in settings.items():
		frappe.db.set_value(doctype, None, values)
