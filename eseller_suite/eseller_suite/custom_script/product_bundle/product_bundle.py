# Copyright (c) 2025, efeone and contributors
# For license information, please see license.txt

import frappe

def mark_item_as_bundle(doc, method):
	if doc.new_item_code:
		frappe.db.set_value("Item", doc.new_item_code, "is_bundle_item", 1)
