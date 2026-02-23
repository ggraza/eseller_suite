from datetime import datetime
import frappe
from frappe.model.document import flt
from pytz import timezone

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

def add_bundle_components_to_stock_entry(se,bundle_item_code,bundle_qty,source_warehouse=None,target_warehouse=None):
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
		se.append("items", {
			"item_code": component.item_code,
			"qty": component_qty,
			"transfer_qty": component_qty,
			"uom": component_stock_uom,
			"stock_uom": component_stock_uom,
			"conversion_factor": 1,
			"s_warehouse": source_warehouse,
			"t_warehouse": target_warehouse,
			"allow_zero_valuation_rate": 1
		})