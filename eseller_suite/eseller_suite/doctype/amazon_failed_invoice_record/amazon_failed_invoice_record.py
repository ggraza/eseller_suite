# Copyright (c) 2025, efeone and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AmazonFailedInvoiceRecord(Document):
	def after_insert(self):
		self.delete_old_failed_invoice_record_if_any()

	def delete_old_failed_invoice_record_if_any(self):
		existing_failed_invoice_record = frappe.db.exists(
			"Amazon Failed Invoice Record",
			{
				"invoice_id": self.invoice_id,
				"name": ["!=", self.name]
			}
		)

		if existing_failed_invoice_record:
			frappe.delete_doc("Amazon Failed Invoice Record", existing_failed_invoice_record, ignore_permissions=True, force=True)
