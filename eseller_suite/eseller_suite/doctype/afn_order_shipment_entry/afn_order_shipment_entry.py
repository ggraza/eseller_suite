# Copyright (c) 2026, efeone and contributors
# For license information, please see license.txt

import os
import csv
from charset_normalizer import from_path

import frappe
from frappe.model.document import Document
from frappe.core.doctype.submission_queue.submission_queue import queue_submission


class AFNOrderShipmentEntry(Document):
	def submit(self):
		queue_submission(self, '_submit')

	def on_submit(self):
		self.process_afn_shipement_file()

	def process_afn_shipement_file(self):
		'''Fetch and validate the attached STN CSV file.'''
		if not self.afn_shipment_file:
			return

		attached_file = frappe.get_doc('File', {'file_url': self.afn_shipment_file})
		file_path = frappe.get_site_path('private', 'files', attached_file.file_name)

		if not os.path.exists(file_path):
			frappe.throw(f'AFN Shipemnt File not found at path: {file_path}')

		if attached_file.file_url.lower().endswith('.csv'):
			self.process_afn_shipement_csv(file_path)
		else:
			frappe.throw('Unsupported file format. Only CSV files are supported for AFN Shipemnt File.')

	def process_afn_shipement_csv(self, file_path):
		'''Read CSV and get row wise data'''
		try:
			detected = from_path(file_path).best()
			encoding = detected.encoding or 'utf-8'

			with open(file_path, 'r', encoding=encoding, newline='') as file:
				csv_reader = csv.DictReader(file, delimiter='\t')

				for row in csv_reader:
					self.create_afn_shipment_log(row)

		except Exception as e:
			error_message = f'Error processing AFN Shipment CSV file: {str(e)}'
			frappe.throw(error_message)

	def create_afn_shipment_log(self, row):
		'''Map CSV row and create AFN Shipemnt Log Entries.'''
		key_mapping = {
			'amazon-order-id': 'amazon_order_id',
			'shipment-id': 'shipment_id',
			'amazon-order-item-id': 'amazon_order_item_id',
			'tracking-number': 'tracking_number',
			'fulfillment-center-id': 'fc_code',
			'sku': 'merchant_sku',
			'quantity-shipped': 'qty',
			'item-price': 'item_price',
			'item-tax': 'item_tax',
		}

		afn_shipment_row = {}

		for csv_key, fieldname in key_mapping.items():
			value = row.get(csv_key)
			if value:
				afn_shipment_row[fieldname] = value.strip() if isinstance(value, str) else value
				afn_shipment_row['afn_order_shipment_entry'] = self.name
				afn_shipment_row['doctype'] = 'AFN Order Shipment Log'
		
		amazon_order_id = afn_shipment_row.get('amazon_order_id', '')
		amazon_order_item_id = afn_shipment_row.get('amazon_order_item_id', '')
		if not amazon_order_id or not amazon_order_item_id:
			return
		try:
			if not frappe.db.exists('AFN Order Shipment Log', { 'amazon_order_id':amazon_order_id, 'amazon_order_item_id': amazon_order_item_id }):
				frappe.get_doc(afn_shipment_row).insert(ignore_permissions=True)
		except Exception as e:
			error_msg = f'Error while creating AFN Shipment Log : {str(e)}'
			frappe.log_error(title=f'AFN Log creation failed ID :{self.name}', message=error_msg)
