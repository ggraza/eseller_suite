import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	print('Updating is_bundle_item for all Product Bundle items...')

	create_custom_fields({
		'Item': [
			{
				'fieldname': 'is_bundle_item',
				'fieldtype': 'Check',
				'label': 'Is Bundle Item',
				'insert_after': 'has_variants',
				'hidden': 1,
			}
		]
	})

	bundle_items = frappe.db.sql_list('''
		SELECT
			DISTINCT new_item_code
		FROM
			`tabProduct Bundle`
		WHERE
			disabled = 0
	''')

	if not bundle_items:
		return

	frappe.db.set_value('Item', {'name': ['in', bundle_items], 'is_bundle_item':0 }, 'is_bundle_item', 1)
