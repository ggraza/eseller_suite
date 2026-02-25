from pytz import timezone

from datetime import datetime

import frappe
from frappe import _
from frappe.utils import flt

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
			"set_basic_rate_manually": 1
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
