# Copyright (c) 2026, efeone and contributors
# For license information, please see license.txt

import io
import gzip
import zipfile

import frappe
import requests
from frappe.model.document import Document
from frappe.utils.file_manager import save_file


class AmazonReportAPILog(Document):
	def validate(self):
		if self.report_url and not self.file_processed:
			if self.report_type == 'GET_GST_STR_ADHOC':
				self.handle_file_upload('Amazon STN Entry', 'stn_file')
			elif self.report_type == 'GET_AMAZON_FULFILLED_SHIPMENTS_DATA_GENERAL':
				self.handle_file_upload('AFN Order Shipment Entry', 'afn_shipment_file', 1)
			else:
				self.handle_file_upload()

	def handle_file_upload(self, dt=None, df=None, submit=0):
		# Get CSV text + original filename
		csv_text, filename = _unwrap_and_decode(
			requests.get(self.report_url, timeout=60).content
		)

		if not filename:
			filename = f"sp_api_report{self.name}.csv"

		filename = filename.split("/")[-1]  # safety

		# Convert to bytes (save_file expects bytes)
		csv_bytes = csv_text.encode("utf-8")

		# Save to File doctype
		file_doc = save_file(
			fname=filename,
			content=csv_bytes,
			dt=self.doctype,
			dn=self.name,
			is_private=1
		)

		if dt and df:
			doc = frappe.new_doc(dt)
			doc.update({
				df: file_doc.file_url
			})
			doc.flags.ignore_mandatory = True
			doc.save()
			if submit:
				try:
					doc.submit()
				except:
					pass
			self.reference_dt = doc.doctype
			self.reference_dn = doc.name
		self.file_processed = 1

@frappe.whitelist()
def get_report_status(report_log_id):
	'''
		Get the status of a report by its ID
	'''
	if not frappe.db.exists("Amazon Report API Log", report_log_id):
		return
	amz_settings = frappe.get_all(
		"Amazon SP API Settings",
		filters={"is_active": 1},
		pluck="name",
		limit=1,
	)
	if not amz_settings:
		return
	
	self = frappe.get_doc("Amazon SP API Settings", amz_settings[0])
	from eseller_suite.eseller_suite.doctype.amazon_sp_api_settings.amazon_sp_api import (
		ReportAPIs,
	)
	
	try:
		# Initialize SupplySources API
		report_api = ReportAPIs(
			client_id=self.client_id,
			client_secret=self.get_password("client_secret"),
			refresh_token=self.refresh_token,
			country_code=self.country,
		)

		try:
			report_id = frappe.db.get_value("Amazon Report API Log", report_log_id, "report_id")
			reports_response = report_api.get_report_document(
				report_id=report_id
			)
			if reports_response:
				if reports_response.get('processingStatus'):
					frappe.db.set_value("Amazon Report API Log", report_log_id, "report_processing_status", reports_response['processingStatus'])
				if reports_response.get('reportDocumentId'):
					frappe.db.set_value("Amazon Report API Log", report_log_id, "report_document_id", reports_response['reportDocumentId'])
			return reports_response
			
		except Exception as api_error:
			# If the endpoint fails, log error and return
			error_details = str(api_error)
			frappe.log_error(title='Error creating Amazon report', message=f"Error details: {error_details}")
			return None
		
	except Exception as e:
		error_msg = str(e)
		frappe.log_error(
			title="Error creating Amazon report",
			message=f"Error: {error_msg}"
		)
		return None

@frappe.whitelist()
def get_report_url(report_log_id):
	'''
		Get the status of a report by its ID
	'''
	if not frappe.db.exists("Amazon Report API Log", report_log_id):
		frappe.log_error(title="Amazon Report API Log Not Found", message=f"Report Log {report_log_id} does not exist.")
		return

	report_document_id = frappe.db.get_value("Amazon Report API Log", report_log_id, "report_document_id")
	if not report_document_id:
		return

	amz_settings = frappe.get_all(
		"Amazon SP API Settings",
		filters={"is_active": 1},
		pluck="name",
		limit=1,
	)
	if not amz_settings:
		frappe.log_error(title="Amazon SP API Settings Not Found", message="No active Amazon SP API Settings found.")
		return
	
	self = frappe.get_doc("Amazon SP API Settings", amz_settings[0])
	from eseller_suite.eseller_suite.doctype.amazon_sp_api_settings.amazon_sp_api import (
		ReportAPIs,
	)
	
	try:
		# Initialize SupplySources API
		report_api = ReportAPIs(
			client_id=self.client_id,
			client_secret=self.get_password("client_secret"),
			refresh_token=self.refresh_token,
			country_code=self.country,
		)

		try:
			
			reports_response = report_api.get_report_document_url(
				report_doc_id=report_document_id
			)
			if reports_response:
				if reports_response.get('url'):
					#Get document and save to trigger doc events for file processing
					report_log_doc = frappe.get_doc("Amazon Report API Log", report_log_id)
					report_log_doc.report_url = reports_response['url']
					report_log_doc.save(ignore_permissions=True)
				return reports_response
			
		except Exception as api_error:
			# If the endpoint fails, log error and return
			error_details = str(api_error)
			frappe.log_error(title='Error creating Amazon report', message=f"Error details: {error_details}")
			return None
		
	except Exception as e:
		error_msg = str(e)
		frappe.log_error(
			title="Error creating Amazon report",
			message=f"Error: {error_msg}"
		)
		return None

def _unwrap_and_decode(data: bytes, filename: str | None = None):
	"""
		Recursively unwrap ZIP / GZIP layers.
		Returns (csv_text, filename)
	"""

	# ZIP container (filename lives here most of the time)
	if data[:4] == b"PK\x03\x04":
		with zipfile.ZipFile(io.BytesIO(data)) as zf:
			name = zf.namelist()[0]
			data = zf.read(name)
		return _unwrap_and_decode(data, filename=name)

	# GZIP container (filename is usually empty, but try)
	if data[:2] == b"\x1f\x8b":
		with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
			data = gz.read()
			gz_name = gz.name or filename
		return _unwrap_and_decode(data, filename=gz_name)

	# ---- Decode CSV text (encoding-aware) ----
	for encoding in ("utf-8", "utf-16", "utf-16le", "latin-1"):
		try:
			return data.decode(encoding), filename
		except UnicodeDecodeError:
			continue

	return data.decode("utf-8", errors="replace"), filename

def get_report_status_scheduler():
	'''
		Scheduled function to check status of all pending reports
	'''
	if not frappe.db.get_single_value("eSeller Settings", "enable_report_scheduler"):
		return
	pending_reports = frappe.get_all("Amazon Report API Log",
		filters={"report_processing_status": ['!=', 'DONE'], "file_processed": 0},
		pluck="name"
	)
	for report_log_id in pending_reports:
		response = get_report_status(report_log_id)
		if response:
			get_report_url(report_log_id)
