from frappe import _
import frappe 
def execute(filters=None):
    data = []
    columns = [
        _("Product 1"),
        _("Product 2"),
        _("Number of Orders"),
        _("Total Amount"),
    ]

    query = """
        SELECT t1.item_name AS product_1, t2.item_name AS product_2, COUNT(*) AS orders, SUM(t1.amount + t2.amount) AS total_amount
        FROM `tabSales Invoice Item` t1
        INNER JOIN `tabSales Invoice Item` t2 ON t1.parent = t2.parent AND t1.item_code < t2.item_code
        WHERE t1.docstatus = 1 AND t2.docstatus = 1
        GROUP BY t1.item_code, t2.item_code
        HAVING orders > 1
        ORDER BY orders DESC
    """

    results = frappe.db.sql(query, as_dict=True)

    for row in results:
        data.append([
            row.product_1,
            row.product_2,
            row.orders,
            row.total_amount,
        ])

    return columns, data