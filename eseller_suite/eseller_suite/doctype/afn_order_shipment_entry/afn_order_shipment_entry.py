# Copyright (c) 2026, efeone and contributors
# For license information, please see license.txt

import os
import csv
from charset_normalizer import from_path

import frappe
from frappe.model.document import Document
from frappe.core.doctype.submission_queue.submission_queue import queue_submission


KEY_MAPPING = {
	'amazon-order-id': 'amazon_order_id',
	'shipment-id': 'shipment_id',
	'shipment-item-id': 'shipment_item_id',
	'amazon-order-item-id': 'amazon_order_item_id',
	'tracking-number': 'tracking_number',
	'fulfillment-center-id': 'fc_code',
	'sku': 'merchant_sku',
	'quantity-shipped': 'qty',
	'item-price': 'item_price',
	'item-tax': 'item_tax',
}

class AFNOrderShipmentEntry(Document):
	def submit(self):
		queue_submission(self, '_submit')

	def on_submit(self):
		self.process_afn_shipement_file()

	def on_trash(self):
		self.delete_linked_documents()

	def process_afn_shipement_file(self):
		"""Fetch and validate the attached STN CSV file."""
		if not self.afn_shipment_file:
			return

		attached_file = frappe.get_doc('File', {'file_url': self.afn_shipment_file})
		file_path = frappe.get_site_path('private', 'files', attached_file.file_name)

		if not os.path.exists(file_path):
			frappe.throw(f'AFN Shipment File not found at path: {file_path}')

		if not attached_file.file_url.lower().endswith('.csv'):
			frappe.throw('Unsupported file format. Only CSV files are supported for AFN Shipment File.')

		self.process_afn_shipement_csv(file_path)

	def process_afn_shipement_csv(self, file_path):
		"""Read CSV, parse all rows, then bulk-create logs."""
		try:
			detected = from_path(file_path).best()
			encoding = detected.encoding or 'utf-8'

			with open(file_path, 'r', encoding=encoding, newline='') as fh:
				rows = list(csv.DictReader(fh, delimiter='\t'))

		except Exception as e:
			frappe.throw(f'Error reading AFN Shipment CSV file: {e}')

		self.bulk_create_afn_shipment_logs(rows)

	def parse_row(self, row):
		"""
		Map a single CSV row dict → fieldname dict.
		Returns None when mandatory keys are missing.
		"""
		mapped = {}
		for csv_key, fieldname in KEY_MAPPING.items():
			value = row.get(csv_key)
			if value:
				mapped[fieldname] = value.strip() if isinstance(value, str) else value

		# Skip rows that lack the two required identifiers
		if not mapped.get('amazon_order_id') or not mapped.get('shipment_item_id'):
			return None

		mapped['afn_order_shipment_entry'] = self.name
		return mapped

	def fetch_existing_pairs(self, parsed_rows):
		"""
		Single query to fetch all (amazon_order_id, shipment_item_id) pairs
		that already exist — avoids N individual frappe.db.exists calls.
		"""
		order_ids = list({r['amazon_order_id'] for r in parsed_rows})

		existing_logs = frappe.get_all(
			'AFN Order Shipment Log',
			filters={'amazon_order_id': ('in', order_ids)},
			fields=['amazon_order_id', 'shipment_item_id'],
			ignore_permissions=True,
		)

		return {(log['amazon_order_id'], log['shipment_item_id']) for log in existing_logs}

	def bulk_create_afn_shipment_logs(self, rows):
		"""
		Parse all CSV rows, resolve which are new in one batch query,
		then insert only the new ones — preserving validate / after_insert
		hooks on AFN Order Shipment Log (which in turn fire hooks on
		Amazon Report API Log).
		"""
		# Parse every row; drop invalid ones early
		parsed_rows = [r for r in (parse_row_safe(self, row) for row in rows) if r]

		if not parsed_rows:
			return

		# One DB round-trip to find already-existing pairs
		existing_pairs = self.fetch_existing_pairs(parsed_rows)

		new_rows = [
			r for r in parsed_rows
			if (r['amazon_order_id'], r['shipment_item_id']) not in existing_pairs
		]

		if not new_rows:
			return

		# Insert new records individually so that validate / after_insert
		#  hooks fire properly — this is intentional since Amazon Report API
		#  Log has hooks that must not be bypassed.
		failed = 0
		for row_data in new_rows:
			try:
				frappe.get_doc({'doctype': 'AFN Order Shipment Log', **row_data}).insert(
					ignore_permissions=True
				)
			except Exception as e:
				failed += 1
				frappe.log_error(
					title=f'AFN Log creation failed — Entry: {self.name}',
					message=(
						f"Order ID : {row_data.get('amazon_order_id')}\n"
						f"Item ID  : {row_data.get('shipment_item_id')}\n"
						f"Error    : {e}"
					),
				)

		if failed:
			frappe.msgprint(
				f'{failed} row(s) could not be inserted. Check the Error Log for details.',
				indicator='orange',
				alert=True,
			)

	def delete_linked_documents(self):
		"""Delete linked documents when the main document is trashed."""
		filters_map = {
			'Submission Queue': {'ref_doctype': self.doctype, 'ref_docname': self.name},
			'AFN Order Shipment Log': {'afn_order_shipment_entry': self.name},
			'Amazon Report API Log': {'reference_dt': self.doctype, 'reference_dn': self.name},
		}

		for doctype, filters in filters_map.items():
			if frappe.db.exists(doctype, filters):
				frappe.db.delete(doctype, filters)

def parse_row_safe(doc, row):
	"""Thin wrapper so the list-comprehension above stays clean."""
	try:
		return doc.parse_row(row)
	except Exception:
		return None
