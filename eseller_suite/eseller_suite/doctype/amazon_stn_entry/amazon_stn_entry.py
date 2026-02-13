# Copyright (c) 2026, efeone and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime

import os
import csv
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
			error_message = f"Error processing STN CSV file: {str(e)}"
			frappe.throw(error_message)

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

		if is_blank_row:
			return

		if stn_row.get("invoice_date_str"):
			dt = get_datetime(stn_row.get("invoice_date_str"))
			stn_row["invoice_date"] = dt.date()
			stn_row["invoice_time"] = dt.time()

		child = self.append("stn_entries", stn_row)
		self.map_companies_and_warehouses(child)
		self.map_and_update_item(child)
		self.set_ready_to_process(child)

	def map_companies_and_warehouses(self, row):
		"""Map companies and warehouses for the STN row."""
		# Set source company and warehouse
		row.source_company = self.get_company_from_gstin(row.source_gstin)
		if row.source_company:
			source_wh = self.get_warehouse_by_code(code=row.source_fc, row=row)
			if source_wh:
				row.source_warehouse = source_wh
			else:
				self.add_error_log(row,f"Source Warehouse not found for code: {row.source_fc} and company: {row.source_company}")
		else:
			self.add_error_log(row, f"Source Company not found for GSTIN: {row.source_gstin}")

		# Set target company and warehouse
		row.target_company = self.get_company_from_gstin(row.target_gstin)
		if row.target_company:
			target_wh = self.get_warehouse_by_code(code=row.target_fc, row=row)
			if target_wh:
				row.target_warehouse = target_wh
			else:
				self.add_error_log(row,f"Target Warehouse not found for code: {row.target_fc} and company: {row.target_company}")
		else:
			self.add_error_log(row,f"Target Company not found for GSTIN: {row.target_gstin}")

	def get_warehouse_by_code(self, code, row):
		"""Get or create warehouse by Amazon code for given company."""
		allow_create = frappe.get_single_value("eSeller Settings", "allow_missing_warehouse_creation")
		wh = frappe.db.get_value("Warehouse", {"amazon_warehouse_code": code}, "name")

		if wh:
			return wh
		if allow_create:
			city = row.source_fc_city if code == row.source_fc else row.target_fc_city
			state = row.source_fc_state if code == row.source_fc else row.target_fc_state
			pin = row.source_fc_pin if code == row.source_fc else row.target_fc_pin
			company = row.source_company if code == row.source_fc else row.target_company
			return self.create_missing_warehouse(row=row, code=code, city=city, state=state, pin=pin, company=company)
		return None

	def create_missing_warehouse(self, row, code, city, state, pin, company):
		"""Create and return a missing Warehouse for the given company."""
		existing_wh = frappe.db.exists("Warehouse", {"amazon_warehouse_code": code})
		if existing_wh:
			return existing_wh

		parent_wh = self.get_parent_warehouse_for_company(company)
		if not parent_wh:
			self.add_error_log(row, f"No Parent Warehouse for Company {company}")
			return None

		try:
			wh = frappe.get_doc({
				"doctype": "Warehouse",
				"warehouse_name": code,
				"amazon_warehouse_code": code,
				"city": city,
				"state": state,
				"pin": pin,
				"company": company,
				"parent_warehouse": parent_wh,
				"is_group": 0
			}).insert(ignore_permissions=True)

			return wh.name

		except Exception as e:
			exception_message = f"Error creating warehouse for code {code} and company {company}: {str(e)}"
			self.add_error_log(row, exception_message)
			return None

	def get_parent_warehouse_for_company(self, company):
		"""Return configured parent warehouse for the given company."""
		return frappe.db.get_value("eSeller Parent Warehouse",{"parent": "eSeller Settings", "company": company},"default_parent_warehouse")

	def get_company_from_gstin(self, gstin):
		"""Return Company mapped to the given GSTIN."""
		return frappe.db.get_value("Company", {"gstin": gstin}, "name")

	def get_item_with_asin(self, asin):
		"""Return Item mapped to the given ASIN."""
		return frappe.db.get_value("Item", {"amazon_item_code": asin}, "name")

	def map_and_update_item(self, row):
		"""Map Item to row using ASIN and update HSN code if missing."""
		if row.asin:
			item = self.get_item_with_asin(row.asin)
			if item:
				row.item = item

				#Update HSN code in Item master if missing
				item_hsn = frappe.db.get_value("Item", item, "gst_hsn_code")
				if not item_hsn and row.hsn_code:
					frappe.db.set_value("Item", item, "gst_hsn_code", row.hsn_code)
			else:
				self.add_error_log(row, f"Item not found for ASIN: {row.asin}")

	def add_error_log(self, row, error_message):
		"""Append error message to row's error_log field."""
		if row:
			if row.error_log:
				row.error_log += f"\n{error_message}"
			else:
				row.error_log = error_message
		else:
			frappe.log_error(message=f"Error log entry attempted but row is None: {error_message}", title="Amazon STN Entry Error")

	def set_ready_to_process(self, row):
		"""Set ready flag if all required mappings are available."""
		if (row.source_company and row.target_company and row.source_warehouse and row.target_warehouse and row.item):
			row.ready_to_process = 1
		else:
			row.ready_to_process = 0

	@frappe.whitelist()
	def get_error_message_html(self):
		"""
			Generate HTML for error messages from child table entries.
		"""
		# Collect rows first (faster than string concatenation in loop)
		error_rows = []

		for entry in self.stn_entries:
			if entry.error_log:
				formatted_log = entry.error_log.replace("\n", "<br>")
				error_rows.append(
					f"<strong>Row {entry.idx}:</strong><br>{formatted_log}"
				)

		if not error_rows:
			return ""

		error_content = "<br><br>".join(error_rows)

		error_html = f"""
			<div style="max-height: 300px; overflow-y: auto;">
				<div style="
					position: sticky;
					top: 0;
					background: #fff;
					padding: 10px;
					z-index: 10;
				">
					<strong style="color: #f00;">
						Errors found in the uploaded STN file:
					</strong>
				</div>
				<div style="padding: 10px;">
					{error_content}
				</div>
			</div>
		"""
		return error_html
