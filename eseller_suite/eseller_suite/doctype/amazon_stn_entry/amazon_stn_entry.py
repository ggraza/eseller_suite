# Copyright (c) 2026, efeone and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import csv
import os
from charset_normalizer import from_path

class AmazonSTNEntry(Document):
	def validate(self):
		if not self.stn_entries:
			self.process_stn_file()

	def process_stn_file(self):
		"""Fetch and validate the attached STN CSV file."""
		if not self.stn_file:
			return

		attached_file = frappe.get_doc("File", {"file_url": self.stn_file})
		file_path = frappe.get_site_path("private", "files", attached_file.file_name)

		if not os.path.exists(file_path):
			frappe.throw(f"STN File not found at path: {file_path}")

		if attached_file.file_url.lower().endswith(".csv"):
			self.process_stn_csv(file_path)
		else:
			frappe.throw("Unsupported file format. Only CSV files are supported for STN File.")

	def process_stn_csv(self, file_path):
		"""Read CSV and append rows to child table."""
		try:
			detected = from_path(file_path).best()
			encoding = detected.encoding

			with open(file_path, "r", encoding=encoding) as file:
				csv_reader = csv.DictReader(file)

				for row in csv_reader:
					self.save_stn_entry_row(row)

		except Exception as e:
			frappe.throw(f"Error processing STN CSV file: {e}")

	def save_stn_entry_row(self, row):
		"""Map CSV row and append to STN Entries."""
		key_mapping = {
			"Gstin Of Receiver": "target_gstin",
			"Transaction Type": "transaction_type",
			"Transaction Id": "transaction_id",
			"Order Id": "order_id",
			"Ship From Fc": "source_fc",
			"Ship From City": "source_fc_city",
			"Ship From State": "source_fc_state",
			"Ship From Postal Code": "source_fc_pin",
			"Ship To Fc": "target_fc",
			"Ship To City": "target_fc_city",
			"Ship To State": "target_fc_state",
			"Ship To Postal Code": "target_fc_pin",
			"Invoice Number": "invoice_number",
			"Invoice Date": "invoice_date_str",
			"Invoice Value": "invoice_value",
			"Asin": "asin",
			"Quantity": "qty",
			"Hsn Code": "hsn_code",
			"Taxable Value": "taxable_value",
			"Igst Rate": "igst_rate",
			"Igst Amount": "igst_amount",
			"Gstin Of Supplier": "source_gstin",
			"Irn Number": "irn_number",
			"Irn Filing Status": "irn_filing_status",
			"Irn Date": "irn_date",
		}

		stn_row = {}
		is_blank_row = True

		for csv_key, fieldname in key_mapping.items():
			value = row.get(csv_key)

			if value:
				is_blank_row = False
				stn_row[fieldname] = value.strip() if isinstance(value, str) else value

		if not is_blank_row:
			self.append("stn_entries", stn_row)

