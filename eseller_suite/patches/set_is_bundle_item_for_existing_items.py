import frappe

def execute():
	print("Updating is_bundle_item for all Product Bundle items...")

	bundle_items = frappe.db.sql_list("""
		SELECT DISTINCT new_item_code
		FROM `tabProduct Bundle`
		WHERE disabled = 0
	""")

	if not bundle_items:
		return

	frappe.db.set_value("Item", {"name": ["in", bundle_items]}, "is_bundle_item", 1)

