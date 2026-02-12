# Copyright (c) 2024, efeone and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class eSellerSettings(Document):
	pass


@frappe.whitelist()
def get_all_companies():
	"""
	Returns all Companies for use in eSeller Settings child table population.
	No client-side DB access is used.
	"""
	return frappe.get_all("Company", fields=["name"], order_by="name asc")
