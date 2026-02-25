# Copyright (c) 2025, efeone and contributors
# For license information, please see license.txt

import frappe

def validate(doc, method):
	'''
		Method which trigger on validate event of Purhcase Invoice
	'''
	set_bundle_diff_amount(doc)

def before_submit(doc, method):
	doc.custom_ready_to_submit = 1

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

def set_bundle_diff_amount(doc):
	'''
		Method to set bundle differences and total
	'''
	#Calculating based on Items table
	total_bundle_amount = 0
	for row in doc.items:
		if row.from_bundle_item:
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
