from pytz import timezone

from datetime import datetime

import frappe
from frappe import _
from frappe.utils import flt, getdate
from erpnext.accounts.utils import get_fiscal_year

def format_date_time_to_ist(utc_time_str):
	# Parse the UTC time string
	utc_time = datetime.strptime(utc_time_str, '%Y-%m-%dT%H:%M:%SZ')

	# Convert to IST
	utc_zone = timezone('UTC')
	ist_zone = timezone('Asia/Kolkata')

	# Localize the UTC time
	utc_time = utc_zone.localize(utc_time)

	# Convert to IST
	ist_time = utc_time.astimezone(ist_zone)
	return ist_time.strftime('%Y-%m-%d %H:%M:%S')

def add_bundle_components_to_stock_entry(se, bundle_item_code, bundle_qty, bundle_rate, source_warehouse=None, target_warehouse=None):
	"""
	Expands a Product Bundle into its component items
	and appends them into Stock Entry items table.

	:param se: Stock Entry document object
	:param bundle_item_code: Parent bundle item code
	:param bundle_qty: Quantity of bundle
	:param source_warehouse: Source warehouse
	:param target_warehouse: Target warehouse
	"""
	bundle_components = frappe.get_all("Product Bundle Item",filters={"parent": bundle_item_code},fields=["item_code", "qty"])
	if not bundle_components:
		frappe.log_error(f"No components found for Bundle Item {bundle_item_code}")

	# Expand components into Stock Entry items
	for component in bundle_components:
		component_stock_uom = frappe.db.get_value("Item",component.item_code,"stock_uom")
		component_qty = flt(bundle_qty) * flt(component.qty)
		component_rate = flt(bundle_rate) / flt(component.qty)
		se.append("items", {
			"item_code": component.item_code,
			"qty": component_qty,
			"basic_rate": component_rate,
			"transfer_qty": component_qty,
			"uom": component_stock_uom,
			"stock_uom": component_stock_uom,
			"conversion_factor": 1,
			"s_warehouse": source_warehouse,
			"t_warehouse": target_warehouse,
			"allow_zero_valuation_rate": 1,
			"set_basic_rate_manually": 1,
			"from_bundle_item": 1,
		})

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
			['item_name', 'last_purchase_rate', 'stock_uom'],
			as_dict=True
		)

		if not item_doc:
			frappe.throw(
				_("Item {0} in Product Bundle {1} does not exist.")
				.format(frappe.bold(item['item_code']), frappe.bold(bundle_item))
			)

		item['item_name'] = item_doc.item_name
		item['rate'] = flt(item_doc.last_purchase_rate or 0)
		item['uom'] = item_doc.stock_uom

	return bundle_items

def get_draft_sales_invoices_without_items():
	'''
		Returns Draft Sales Invoice that do not contain any items.
	'''
	query = """
		SELECT
			si.name,
			si.amazon_order_id
		FROM
			`tabSales Invoice` si
		LEFT JOIN `tabSales Invoice Item` sii
			ON sii.parent = si.name
		WHERE
			si.docstatus = 0
		GROUP BY si.amazon_order_id
		HAVING COUNT(sii.name) = 0
	"""
	invoices = frappe.db.sql(query, as_dict=True)
	return invoices

@frappe.whitelist()
def update_sales_invoice_with_items(invoice_id, amazon_order_id):
	'''
		Update missing items on Sales Invoice from Sales Order.
	'''
	si_doc = frappe.get_doc("Sales Invoice", invoice_id)
	so = frappe.db.get_value("Sales Order", {"amazon_order_id": amazon_order_id}, "name")
	if so:
		so_doc = frappe.get_doc("Sales Order", so)

		si_doc.items = []
		for item in so_doc.items:
			si_row = item.as_dict()
			si_row['so_detail'] = item.name
			si_row['sales_order'] = item.parent
			si_row.pop('doctype')
			si_row.pop('parenttype')
			si_row.pop('name')
			si_row.pop('parent')
			si_doc.append("items", si_row)

		si_doc.taxes = []
		for tax in so_doc.taxes:
			tax_row = tax.as_dict()
			tax_row.pop('doctype')
			tax_row.pop('parenttype')
			tax_row.pop('name')
			tax_row.pop('parent')
			si_doc.append("taxes", tax_row)

		si_doc.packed_items = []
		for packed_item in so_doc.packed_items:
			packed_item_row = packed_item.as_dict()
			packed_item_row.pop('doctype')
			packed_item_row.pop('parenttype')
			packed_item_row.pop('name')
			packed_item_row.pop('parent')
			si_doc.append("packed_items", packed_item_row)

	si_doc.save(ignore_permissions=True)
	return si_doc.name

@frappe.whitelist()
def update_missing_items_in_sales_invoices(max_count=250):
	'''
		Update missing items on Draft Sales Invoices from Sales Orders.
	'''
	invoices = get_draft_sales_invoices_without_items()
	if len(invoices) > max_count:
		invoices = invoices[:max_count]
	for invoice in invoices:
		try:
			update_sales_invoice_with_items(invoice.name, invoice.amazon_order_id)
		except Exception as e:
			frappe.log_error(message=f"Error updating Sales Invoice {invoice.name} with items: {str(e)}", title="Update Sales Invoice Items")
	return len(invoices)

@frappe.whitelist()
def delete_submitted_invoices_without_stock(max_count=100):
	'''
		Delete submitted Sales Invoices that do not have any Stock Items.
	'''
	filters = {
		'voucher_type': 'Sales Invoice',
		'qty_after_transaction': ['<', 0],
		'is_cancelled': 0,
		'voucher_no': ['like', 'AMZ-%']
	}
	sales_invoices = frappe.db.get_all('Stock Ledger Entry', filters=filters, pluck='voucher_no', limit_page_length=max_count)
	sales_invoices = list(set(sales_invoices))  # Remove duplicates
	for si in sales_invoices:
		cancel_and_delete_invoice(si)
	return sales_invoices

@frappe.whitelist()
def delete_submitted_so_without_si(max_count=100):
	'''
		Delete submitted Sales Orders that do not have any linked Sales Invoices.
	'''
	query = """
		SELECT
			so.name
		FROM
			`tabSales Order` so
		LEFT JOIN
			`tabSales Invoice Item` sii
			ON sii.sales_order = so.name
		LEFT JOIN
			`tabSales Invoice` si
			ON si.name = sii.parent
		WHERE
			so.docstatus = 1
			AND si.name IS NULL;
	"""
	data = frappe.db.sql(query, as_dict=True)
	sales_orders = [so.name for so in data][:max_count]
	for so in sales_orders:
		try:
			so_doc = frappe.get_doc("Sales Order", so)
			if so_doc.docstatus == 1:
				so_doc.cancel()
				so_doc.delete()
		except Exception as e:
			frappe.log_error(message=f"Error deleting Sales Order {so}: {str(e)}", title="Delete Sales Order")

@frappe.whitelist()
def delete_submitted_invoices_without_gle(max_count=100):
	'''
	Delete submitted Sales Invoices that do not have any linked General Ledger Entries.
	'''
	query = """
		SELECT
			si.name
		FROM
			`tabSales Invoice` si
		LEFT JOIN
			`tabGL Entry` gle
			ON gle.voucher_type = 'Sales Invoice'
			AND gle.voucher_no = si.name
		WHERE
			si.docstatus = 1
			AND gle.name IS NULL
	"""
	data = frappe.db.sql(query, as_dict=True)
	sales_invoices = [si.name for si in data][:max_count]
	for si in sales_invoices:
		cancel_and_delete_invoice(si)

def cancel_and_delete_invoice(invoice_id):
	'''
		Cancel and delete a Sales Invoice by name.
	'''
	if frappe.db.exists('Sales Invoice', invoice_id):
		try:
			si_doc = frappe.get_doc("Sales Invoice", invoice_id)
			if si_doc.docstatus == 1:
				return_si = frappe.db.get_value('Sales Invoice', filters={'return_against': invoice_id, 'docstatus': 1}, pluck='name')
				if return_si:
					cancel_and_delete_invoice(return_si)
				si_doc.cancel()
				si_doc.delete()
		except Exception as e:
			frappe.log_error(message=f"Error deleting Sales Invoice {invoice_id}: {str(e)}", title="Delete Sales Invoice")

def is_old_data(transaction_date):
	'''
		Method to check wether the data is from old date before opening entry is done.
		Will be using date threshold from Configuration
	'''
	opening_date = frappe.db.get_single_value('eSeller Settings', 'opening_date')
	if not opening_date:
		return False
	opening_date = getdate(opening_date)
	transaction_date = getdate(transaction_date)
	op_fy = get_fiscal_year(opening_date)
	tr_fy = get_fiscal_year(transaction_date)
	if tr_fy[1] < op_fy[1]:
		return True
	return False
