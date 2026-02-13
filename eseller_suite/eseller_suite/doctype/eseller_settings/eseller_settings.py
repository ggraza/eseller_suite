# Copyright (c) 2024, efeone and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class eSellerSettings(Document):
	def validate(self):
		self.validate_stn_defaults()

	def validate_stn_defaults(self):
		'''Validates that there are no duplicate companies in the STN Defaults child table.'''
		companies = {row.company for row in self.parent_warehouses}

		if len(companies) != len(self.parent_warehouses):
			frappe.throw(_("Cannot set multiple Parent Warehouses for a company."))

@frappe.whitelist()
def get_all_companies():
	"""
	Returns all Companies for use in eSeller Settings child table population.
	No client-side DB access is used.
	"""
	return frappe.get_all("Company", fields=["name"], order_by="name asc")
