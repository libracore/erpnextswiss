// Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Printable Price List"] = {
	"filters": [
        {
            "fieldname":"price_list",
            "label": __("Price List"),
            "fieldtype": "Link",
            "options": "Price List"
        }
	]
}
