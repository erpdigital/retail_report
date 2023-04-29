# Copyright (c) 2023, Alimerdan Rahimov and contributors
# For license information, please see license.txt

# import frappe

import frappe

def execute(filters=None):
    columns = [
        {
            "label": "Item Code",
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 120
        },
        {
            "label": "Skidka",
            "fieldname": "pr1",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": "Продажа",
            "fieldname": "pr2",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": "Optom",
            "fieldname": "pr3",
            "fieldtype": "Currency",
            "width": 120
        },
          {
            "label": "Optom 2",
            "fieldname": "pr4",
            "fieldtype": "Currency",
            "width": 120
        }
    ]

    data = []
    price_lists = ["Skidka", "Standard Selling","Optom","Optom 2"]
   
    data = frappe.db.sql("""
        SELECT
            `tabItem`.`item_code`,
            IFNULL(`Pr1`.`price_list_rate`, 0) AS `pr1`,
            IFNULL(`Pr2`.`price_list_rate`, 0) AS `pr2`,
            IFNULL(`Pr3`.`price_list_rate`, 0) AS `pr3`
        FROM
            `tabItem`
            LEFT JOIN `tabItem Price` AS `Pr1`
                ON `tabItem`.`item_code` = `Pr1`.`item_code` AND `Pr1`.`price_list` = 'Skidka'
            LEFT JOIN `tabItem Price` AS `Pr2`
                ON `tabItem`.`item_code` = `Pr2`.`item_code` AND `Pr2`.`price_list` = 'Standard Selling'
            LEFT JOIN `tabItem Price` AS `Pr3`
                ON `tabItem`.`item_code` = `Pr3`.`item_code` AND `Pr3`.`price_list` = 'Optom'
                 LEFT JOIN `tabItem Price` AS `Pr4`
                ON `tabItem`.`item_code` = `Pr4`.`item_code` AND `Pr4`.`price_list` = 'Optom 2'
        WHERE
            `tabItem`.`item_group` = '{0}'
        ORDER BY
            `tabItem`.`item_code`
    """.format(filters.get("item_group")), as_dict=True)

    return columns, data