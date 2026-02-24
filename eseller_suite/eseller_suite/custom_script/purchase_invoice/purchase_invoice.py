# Copyright (c) 2025, efeone and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def validate(doc, method):
	'''
		Method which trigger on validate event of Purhcase Invoice
	'''
	set_bundle_diff_amount(doc)
	populate_item_bundle(doc)
	set_bundle_diff_amount(doc)

def on_submit(doc, method):
	'''
		Method which trigger on on_submit event of Purchase Invoice
	'''
	if doc.bundle_difference_amount:
		title = 'Check Difference Amount'
		msg = 'Cannot submit the invoice due to difference amount of {0} for bundle items'.format(frappe.bold(doc.bundle_difference_amount))
		frappe.throw(
			title=title,
			msg=msg
		)

def on_cancel(doc, method):
	'''
		Method which trigger on on_cancel event of Purchase Invoice
	'''
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

def populate_item_bundle(doc):
	"""Expand bundle parent items into child items in Purchase Invoice."""
	bundle_rows = doc.get("bundle_items") or []
	if not bundle_rows:
		return

	populated_items = []

	doc.items = [
		row for row in doc.items
		if not frappe.db.get_value("Item", row.item_code, "is_bundle_item")
	]

	for bundle in bundle_rows:
		if bundle.bundle_processed:
			continue
		children = get_bundle_items(bundle.item_code) or []
		for child in children:
			qty = flt(child.get("qty")) * flt(bundle.qty)
			rate = flt(bundle.get("rate")) / flt(child.get("qty"))
			conversion_factor = 1
			stock_uom = child["uom"]
			populated_items.append({
				"item_code": child["item_code"],
				"item_name": child["item_name"],
				"qty": qty,
				"uom": child["uom"],
				"stock_uom": stock_uom,
				"conversion_factor": conversion_factor,
				"rate": rate,
				"amount": qty * rate,
				"base_rate": rate,
				"base_amount": qty * rate,
				"description": child.get("description"),
				"warehouse": doc.set_warehouse,
				"bundle_parent": bundle.name,
				"bundle_qty": flt(child.get("qty")),
				"item_tax_rate": '{}',
				"taxable_value": qty * rate
			})
		bundle.bundle_processed = 1

	for row in populated_items:
		doc.append("items", row)

	doc.set_missing_values()

def set_bundle_diff_amount(doc):
	'''
		Method to set bundle differences and total
	'''
	#Calculating based on Items table
	total_bundle_amount = 0
	for row in doc.items:
		if row.bundle_parent:
			total_bundle_amount += row.amount
	doc.total_bundle_amount = round(total_bundle_amount, 2)

	#Calculating based on Bundle Items Table
	total_bundle_amount_actual = 0
	for item in doc.bundle_items:
		if item.rate and item.qty:
			item.amount = item.rate * item.qty
		total_bundle_amount_actual += item.amount
	doc.total_bundle_amount_actual = round(total_bundle_amount_actual, 2)

	# Setting Difference Amount
	doc.bundle_difference_amount = round((doc.total_bundle_amount_actual - doc.total_bundle_amount), 2)
