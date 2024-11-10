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
            "label": "Item Name",
            "fieldname": "item_name",
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
        },
       
        {
            "label": "Praýs.Zakaz",
            "fieldname": "pr5",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": "Bedew market",
            "fieldname": "pr6",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": "Arzan baha",
            "fieldname": "pr7",
            "fieldtype": "Currency",
            "width": 120
        },
          {
            "label": "Kemran optom",
            "fieldname": "pr8",
            "fieldtype": "Currency",
            "width": 120
        }
    ]

    data = []
    price_lists = ["Skidka", "Standard Selling","Optom","Optom 2","Praýs.Zakaz","Bedew market","Arzan baha","Kemran optom"]
   
    data = frappe.db.sql("""
        SELECT
            `tabItem`.`item_code`,
            `tabItem`.`item_name`,
            IFNULL(`Pr1`.`price_list_rate`, 0) AS `pr1`,
            IFNULL(`Pr2`.`price_list_rate`, 0) AS `pr2`,
            IFNULL(`Pr3`.`price_list_rate`, 0) AS `pr3`,
            IFNULL(`Pr4`.`price_list_rate`, 0) AS `pr4`,
                IFNULL(`Pr5`.`price_list_rate`, 0) AS `pr5`,
            IFNULL(`Pr6`.`price_list_rate`, 0) AS `pr6`,
            IFNULL(`Pr7`.`price_list_rate`, 0) AS `pr7`,
            IFNULL(`Pr8`.`price_list_rate`, 0) AS `pr8`
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
                LEFT JOIN `tabItem Price` AS `Pr5`
                ON `tabItem`.`item_code` = `Pr5`.`item_code` AND `Pr5`.`price_list` = 'Praýs.Zakaz'
                LEFT JOIN `tabItem Price` AS `Pr6`
                ON `tabItem`.`item_code` = `Pr6`.`item_code` AND `Pr6`.`price_list` = 'Bedew market'
                LEFT JOIN `tabItem Price` AS `Pr7`
                ON `tabItem`.`item_code` = `Pr7`.`item_code` AND `Pr7`.`price_list` = 'Arzan baha'
                LEFT JOIN `tabItem Price` AS `Pr8`
                ON `tabItem`.`item_code` = `Pr8`.`item_code` AND `Pr8`.`price_list` = 'Kemran optom'
        WHERE
            `tabItem`.`item_group` = '{0}'
             AND `tabItem`.`stock_uom` = '{1}' 
             and `tabItem`.`disabled` = 0           
        ORDER BY
            `tabItem`.`item_code`
    """.format(filters.get("item_group"),filters.get("uom")), as_dict=True)

    return columns, data