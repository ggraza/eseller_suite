# Copyright (c) 2025, efeone and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def on_cancel(doc, method):
	doc.ignore_linked_doctypes = (
		"GL Entry",
		"Stock Ledger Entry",
		"Repost Item Valuation",
		"Repost Payment Ledger",
		"Repost Payment Ledger Items",
		"Repost Accounting Ledger",
		"Repost Accounting Ledger Items",
		"Unreconcile Payment",
		"Unreconcile Payment Entries",
		"Payment Ledger Entry",
		"Tax Withheld Vouchers",
		"Serial and Batch Bundle",
		"Amazon STN Entry",
	)

@frappe.whitelist()
def get_bundle_items(bundle_item):
	"""
	Fetch all child items & details from Product Bundle
	"""

	if not frappe.db.exists("Product Bundle", {"name": bundle_item, "disabled": 0}):
		frappe.throw(
			_("Product Bundle {0} does not exist or is disabled.")
			.format(frappe.bold(bundle_item)),
			title=_("Invalid Bundle")
		)

	bundle_items = frappe.db.get_all(
		'Product Bundle Item',
		filters={'parent': bundle_item},
		fields=['item_code', 'qty', 'description'],
		order_by='idx'
	)

	for item in bundle_items:
		item_doc = frappe.get_cached_value(
			"Item",
			item['item_code'],
			['item_name', 'standard_buy_price', 'purchase_uom', 'stock_uom'],
			as_dict=True
		)

		if not item_doc:
			frappe.throw(
				_("Item {0} in Product Bundle {1} does not exist.")
				.format(frappe.bold(item['item_code']), frappe.bold(bundle_item))
			)

		item['item_name'] = item_doc.item_name
		item['rate'] = flt(item_doc.standard_buy_price or 0)
		item['uom'] = item_doc.purchase_uom or item_doc.stock_uom

	return bundle_items

def populate_item_bundle(doc, method=None):
	"""Expand bundle parent items into child items in Purchase Invoice."""

	bundle_rows = doc.get("bundle_items") or []
	if not bundle_rows:
		return

	populated_items = []

	# remove original bundle parent rows from items table
	doc.items = [
		row for row in doc.items
		if not frappe.db.get_value("Item", row.item_code, "is_bundle_item")
	]

	# build populated children
	for bundle in bundle_rows:
		children = get_bundle_items(bundle.item_code)

		for child in children:
			qty = flt(child.get("qty")) * flt(bundle.qty)

			populated_items.append({
				"item_code": child["item_code"],
				"item_name": child["item_name"],
				"qty": qty,
				"uom": child["uom"],
				"rate": flt(child.get("rate")),
				"amount": qty * flt(child.get("rate")),
				"description": child.get("description"),
				"warehouse": doc.set_warehouse,
				"bundle_parent": bundle.name,
				"bundle_qty": flt(child.get("qty")),
			})

	# append children
	for row in populated_items:
		doc.append("items", row)
