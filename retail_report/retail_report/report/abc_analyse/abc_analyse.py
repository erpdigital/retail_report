import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data

def get_columns():
    return [
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": _("Revenue"), "fieldname": "revenue", "fieldtype": "Currency", "width": 150},
        {"label": _("Revenue Contribution (%)"), "fieldname": "revenue_contribution", "fieldtype": "Percent", "width": 150},
        {"label": _("ABC Category"), "fieldname": "abc_category", "fieldtype": "Data", "width": 100}
    ]

def get_data():
    items = frappe.get_all("Item", fields=["name", "item_name"])
    total_revenue = get_total_revenue()

    item_revenues = []
    for item in items:
        item_revenue = get_item_revenue(item.name)
        revenue_contribution = (item_revenue / total_revenue) * 100 if total_revenue else 0
        item_revenues.append({
            "item_code": item.name,
            "item_name": item.item_name,
            "revenue": item_revenue,
            "revenue_contribution": revenue_contribution
        })

    item_revenues.sort(key=lambda x: x["revenue_contribution"], reverse=True)

    data = []
    cumulative_percentage = 0
    for item in item_revenues:
        cumulative_percentage += item["revenue_contribution"]
        category = categorize_item(cumulative_percentage)
        data.append([item["item_code"], item["item_name"], item["revenue"], item["revenue_contribution"], category])

    return data

def get_item_revenue(item_code):
    item_revenue = frappe.db.sql("""
        SELECT SUM(qty * rate) as revenue
        FROM `tabSales Invoice Item`  as si
        inner join `tabSales Invoice` as s on s.name = si.parent
        WHERE si.item_code = %s and  
        s.docstatus =1 
     
        AND si.creation BETWEEN DATE_SUB(NOW(), INTERVAL 1 MONTH) AND NOW()
    """, item_code, as_dict=True)

    return item_revenue[0].get('revenue') or 0

def get_total_revenue():
    total_revenue = frappe.db.sql("""
        SELECT SUM(qty * rate) as total_revenue
        FROM `tabSales Invoice Item` as si 
        inner join `tabSales Invoice` as s on s.name = si.parent
        WHERE 
        s.docstatus =1 
        and
        si.creation BETWEEN DATE_SUB(NOW(), INTERVAL 1 MONTH) AND NOW()
    """, as_dict=True)

    return total_revenue[0].get('total_revenue') or 0

def categorize_item(cumulative_percentage):
    if cumulative_percentage <= 80:
        return 'A'
    elif 80 < cumulative_percentage <= 95:
        return 'B'
    else:
        return 'C'