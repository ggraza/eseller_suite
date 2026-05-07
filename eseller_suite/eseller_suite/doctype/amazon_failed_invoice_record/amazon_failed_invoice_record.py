# Copyright (c) 2025, efeone and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
class AmazonFailedInvoiceRecord(Document):
	def after_insert(self):
		self.delete_old_failed_invoice_records()

	def delete_old_failed_invoice_records(self):
		if not self.invoice_id:
			return

		frappe.db.delete(
			"Amazon Failed Invoice Record",
			{
				"invoice_id": self.invoice_id,
				"name": ["!=", self.name]
			}
		)
