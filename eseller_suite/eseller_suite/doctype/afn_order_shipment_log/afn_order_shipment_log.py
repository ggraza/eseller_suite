# Copyright (c) 2026, efeone and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


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
				self.item_code = self.merchant_sku
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
def check_so_existance_and_rq_job(amazon_order_id, amz_setting_name):
	'''
		Method to check wether RQ Job for Get Order is working or not. Along with Sales Order existance for given Order ID
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
	if frappe.db.exists('Sales Order', { 'amazon_order_id':amazon_order_id, 'docstatus':['!=', 2] }):
		return 0
	return 1