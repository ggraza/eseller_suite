import frappe
from frappe import _


def execute(filters=None):

	columns = [
		{
			"label": _("Amazon Order ID"),
			"fieldname": "amazon_order_id",
			"fieldtype": "Data",
			"width": 220
		},
		{
			"label": _("Grand Total"),
			"fieldname": "grand_total",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 200
		},
		{
			"label": _("Sales Orders"),
			"fieldname": "sales_orders",
			"fieldtype": "Data",
			"width": 400
		},
		{
			"label": _("Total Count"),
			"fieldname": "total_count",
			"fieldtype": "Int",
			"width": 120
		}
	]

	data = get_duplicate_sales_orders()

	return columns, data


def get_duplicate_sales_orders():
	'''
		Method to fetch duplicate sales orders based on amazon_order_id, grand_total and company
	'''
	return frappe.db.sql("""
		SELECT
			amazon_order_id,
			grand_total,
			company,
			GROUP_CONCAT(name ORDER BY creation SEPARATOR ', ') AS sales_orders,
			COUNT(*) AS total_count
		FROM
			`tabSales Order`
		WHERE
			amazon_order_id IS NOT NULL
			AND amazon_order_id != ''
		GROUP BY
			amazon_order_id,
			grand_total,
			company
		HAVING
			COUNT(*) > 1
	""", as_dict=True)

@frappe.whitelist()
def delete_all_duplicate_draft_sales_orders():
	'''
		Method to Delete all duplicate draft sales orders
	'''
	order_ids = []
	duplicate_groups = get_duplicate_sales_orders()
	if not duplicate_groups:
		frappe.throw(_("No duplicate sales orders found to delete."))
	order_ids = [row["amazon_order_id"] for row in duplicate_groups]
	frappe.db.delete("Sales Order", { "amazon_order_id": ["in", order_ids], "docstatus": 0 })
	return {
		"deleted_count": len(order_ids),
		"deleted_orders": order_ids
	}
