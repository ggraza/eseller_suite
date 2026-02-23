# Copyright (c) 2025, efeone and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def mark_item_as_bundle(doc, method):
	if doc.new_item_code:
		frappe.db.set_value("Item", doc.new_item_code, "is_bundle_item", 1)

def validate_product_bundle_items(doc, method):
	"""
	Ensure all Product Bundle items are stock items.
	"""
	for row in doc.items:
		is_stock_item = frappe.db.get_value("Item", row.item_code, "is_stock_item")
		if not is_stock_item:
			frappe.throw(_("Row {0}: Item <b>{1}</b> must be marked as a Stock Item to be added in Product Bundle.").format(row.idx, row.item_code),title=_("Invalid Product Bundle Item"))