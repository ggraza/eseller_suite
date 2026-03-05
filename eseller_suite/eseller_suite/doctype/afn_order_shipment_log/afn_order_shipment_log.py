# Copyright (c) 2026, efeone and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, today
from frappe.model.document import Document
from eseller_suite.eseller_suite.doctype.amazon_sp_api_settings.amazon_repository import get_orders

class AFNOrderShipmentLog(Document):
	def before_save(self):
		self.set_missing_values()

	def add_exceptions(self, exception_msg):
		'''
			Method to add exceptions if any
		'''
		if self.exceptions:
			exception_msg = f"{self.exceptions}\n{exception_msg}"
		self.exceptions = exception_msg

	def set_missing_values(self):
		'''
			Set missing values like Item, Warehosue and Company
		'''
		self.exceptions = ''
		#Setting Item
		if self.merchant_sku and not self.item_code:
			if frappe.db.exists('Item', self.merchant_sku):
				item_code = self.merchant_sku
				if frappe.db.get_value('Item', self.merchant_sku, 'actual_item'):
					item_code = frappe.db.get_value('Item', self.merchant_sku, 'actual_item')
				self.item_code = item_code
			else:
				exception_msg = f"Item not found with SKU : {self.merchant_sku}"
				self.add_exceptions(exception_msg)

		#Setting Item and Company
		if self.fc_code and not self.warehouse:
			if frappe.db.exists('Warehouse', { 'amazon_warehouse_code': self.fc_code }):
				self.warehouse = frappe.db.get_value('Warehouse', { 'amazon_warehouse_code': self.fc_code }, 'name')
				self.company = frappe.db.get_value('Warehouse', { 'amazon_warehouse_code': self.fc_code }, 'company')
			else:
				exception_msg = f"Warehouse not found FC : {self.fc_code}"
				self.add_exceptions(exception_msg)

		#Setting Order Created
		if frappe.db.exists('Sales Invoice', { 'amazon_order_id': self.amazon_order_id }):
			self.order_created = 1

		if self.company and self.warehouse and self.item_code:
			self.exceptions = ''
		self.has_exceptions = 1 if self.exceptions else 0

@frappe.whitelist()
def retry_fetching_selected_logs(docnames):
	'''
		Method to fetch missing values form list view
	'''
	if isinstance(docnames, str):
		docnames = frappe.parse_json(docnames)

	for name in docnames:
		if frappe.db.exists("AFN Order Shipment Log", name):
			doc = frappe.get_doc("AFN Order Shipment Log", name)
			if doc.has_exceptions:
				doc.set_missing_values()
				doc.save()
	return "Success"

@frappe.whitelist()
def check_rq_job_existance(amazon_order_id, amz_setting_name):
	'''
		Method to check wether RQ Job for Get Order is working or not
	'''
	scheduler_rq_jobs = frappe.db.get_all('RQ Job', {
		'job_name': 'eseller_suite.eseller_suite.doctype.amazon_sp_api_settings.amazon_sp_api_settings.schedule_get_order_details',
		'status': ['in', ['queued', 'started']]
	})
	sync_rq_jobs = frappe.db.get_all('RQ Job', {
		'job_name': f'Get Amazon Orders - {amz_setting_name}',
		'status': ['in', ['queued', 'started']]
	})
	if scheduler_rq_jobs or sync_rq_jobs:
		return 0
	return 1

@frappe.whitelist()
def fetch_sales_orders(docnames):
	'''
		Method to fetch missing values from list view
	'''
	last_updated_after = getdate(today())
	amz_setting_name = frappe.db.get_all('Amazon SP API Settings', { 'is_active':1 }, pluck='name', limit=1) or []
	if not amz_setting_name:
		frappe.msgprint("No active Amazon SP API Settings found. Please create and activate one to fetch orders.", indicator='red')
		return
	amz_setting_name = amz_setting_name[0]

	if isinstance(docnames, str):
		docnames = frappe.parse_json(docnames)

	filtered_order_ids = frappe.db.get_all(
		"AFN Order Shipment Log",
		filters={"name": ["in", docnames], "has_exceptions": 0},
		pluck="amazon_order_id",
		limit=20
	)

	# Remove duplicates
	unique_order_ids = list(set(filtered_order_ids))

	# Convert to comma separated string
	amazon_order_ids = ",".join(unique_order_ids)

	orders = get_orders(amz_setting_name=amz_setting_name, last_updated_after=last_updated_after, amazon_order_ids=amazon_order_ids)
	return orders
