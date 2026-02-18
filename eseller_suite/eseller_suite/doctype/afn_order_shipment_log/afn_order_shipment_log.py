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
