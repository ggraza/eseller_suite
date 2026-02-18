import frappe
from frappe.model import _
from frappe.model.base_document import flt

def transfer_barcodes(doc, method=None):
	"""method transfers the barcodes on submit

	Args:
		doc (_type_): _description_
		method (_type_, optional): _description_. Defaults to None.
	"""
	for item in doc.items:
		if not item.barcode_no:
			continue

		barcodes = item.barcode_no.split("\n")
		for barcode in barcodes:
			existing_serial_no = frappe.db.exists(
				"eSeller Serial No",
				{"serial_no": barcode},
			)
			if existing_serial_no:
				serial_doc = frappe.get_doc("eSeller Serial No", existing_serial_no)
				serial_doc.status = "Transferred"
				serial_doc.warehouse = item.t_warehouse
				serial_doc.transfer_document_no = doc.name
				serial_doc.save()
	frappe.msgprint(
		"Serial Numbers are now Transferred",
		alert=True,
	)

def before_insert_custom(doc, method=None):
	"""method corrects warehouse in stock returns from returns & replaced orders if temporary stock transfer is on"""
	if doc.from_return_invoice:
		amz_settings = frappe.get_last_doc("Amazon SP API Settings")
		if amz_settings.temporary_stock_transfer_required:
			si = doc.sales_invoice_no
			return_warehouse = amz_settings.warehouse
			si_fulfillment_channel = frappe.db.get_value("Sales Invoice", si, "fulfillment_channel")

			if si_fulfillment_channel:
				if si_fulfillment_channel == 'AFN':
					return_warehouse = amz_settings.afn_warehouse

			doc.to_warehouse = return_warehouse
			for row in doc.items:
				row.t_warehouse = return_warehouse

def on_canel(doc, method):
	doc.ignore_linked_doctypes = (
		"GL Entry",
		"Stock Ledger Entry",
		"Repost Item Valuation",
		"Serial and Batch Bundle",
		"Amazon STN Entry",
	)

@frappe.whitelist()
def get_bundle_items(bundle_item):
	"""
	method fetches the child items of a bundle item to be added in the stock entry items table
	"""
	if not bundle_item:
		return []

	if not frappe.db.exists("Product Bundle", bundle_item):
		frappe.log_error(_("Product Bundle {0} does not exist").format(bundle_item))
		return []

	bundle_items = frappe.get_all(
		"Product Bundle Item",
		filters={"parent": bundle_item},
		fields=["item_code", "qty", "description"],
		order_by="idx"
	)
	result = []
	for row in bundle_items:
		item_details = frappe.get_cached_value(
			"Item",
			row.item_code,
			["item_name", "stock_uom", "standard_rate"],
			as_dict=True
		)
		result.append({
			"item_code": row.item_code,
			"item_name": item_details.item_name if item_details else "",
			"qty": flt(row.qty),
			"uom": item_details.stock_uom,
			"rate": item_details.standard_rate if item_details else 0,
			"description": row.description
		})
	return result

def populate_item_bundle(doc, method=None):
	"""Expand bundle parent items into child items in Stock Entry."""
	bundle_rows = doc.get("bundle_items")
	if not bundle_rows:
		return

	populated_items = []
	doc.items = [
		row for row in doc.items
		if not frappe.db.get_value("Item", row.item_code, "is_bundle_item")
	]

	for bundle in bundle_rows:
		children = get_bundle_items(bundle.item_code)
		for child in children:
			qty = flt(child.get("qty")) * flt(bundle.qty)
			populated_items.append({
				"item_code": child["item_code"],
				"item_name": child["item_name"],
				"qty": qty,
				"transfer_qty": qty,
				"uom": child["uom"],
				"stock_uom": child["uom"],
				"rate": flt(child.get("rate")),
				"amount": qty * flt(child.get("rate")),
				"description": child.get("description"),
				"bundle_parent": bundle.name,
				"bundle_qty": flt(child.get("qty")),
				"item_tax_rate": '{}',
				"taxable_value": 0,
				"conversion_factor": 1,
				"allow_zero_valuation_rate": 1,
			})

	for row in populated_items:
		doc.append("items", row)
