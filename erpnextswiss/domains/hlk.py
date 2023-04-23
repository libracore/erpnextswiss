from __future__ import unicode_literals

data = {
	'custom_fields': {
		'Customer': [
			{
				'fieldname': 'field_test',
				'fieldtype': 'Data',
				'insert_after': 'customer_name',
				'label': 'Field Test'
			}
		],
		'Item Group': [
			{
				'fieldname': 'bkp_katalog_version',
				'fieldtype': 'Data',
				'insert_after': 'is_group',
				'label': 'BKP Katalog Version'
			}
		],
		"Quotation": [
			{
				"fieldname": "introduction_template",
				"fieldtype": "Link",
				"insert_after": "items_section",
				"label": "Introduction Template",
				"options": "HLK Text Template"
			},
			{
				"fieldname": "introduction",
				"fieldtype": "Text Editor",
				"insert_after": "introduction_template",
				"label": "Introduction"
			},
			{
				"fieldname": "deactivate_page_break",
				"fieldtype": "Check",
				"insert_after": "introduction",
				"label": "Deactivate Page Break"
			},
			{
				"fieldname": "hlk_structur_organisation_template",
				"fieldtype": "Link",
				"insert_after": "deactivate_page_break",
				"label": "HLK Structur Organisation Template",
				"options": "HLK Structur Organisation Template"
			},
			{
				"fieldname": "hlk_structur_organisation",
				"fieldtype": "Table",
				"insert_after": "hlk_structur_organisation_template",
				"label": "HLK Structur Organisation",
				"options": "HLK Structur Organisation"
			},
			{
				"fieldname": "closing_text_template",
				"fieldtype": "Link",
				"insert_after": "items",
				"label": "Closing Text Template",
				"options": "HLK Text Template"
			},
			{
				"fieldname": "closing_text",
				"fieldtype": "Text Editor",
				"insert_after": "closing_text_template",
				"label": "Closing Text"
			},
			{
				"fieldname": "section_special_discounts",
				"fieldtype": "Section Break",
				"insert_after": "discount_amount",
				"label": "Special Discounts"
			},
			{
				"fieldname": "special_discounts",
				"fieldtype": "Table",
				"insert_after": "section_special_discounts",
				"label": "Special Discounts",
				"options": "HLK Discounts"
			}
		],
		"Quotation Item": [
			{
				"fieldname": "hlk_element",
				"fieldtype": "Link",
				"insert_after": "customer_item_code",
				"label": "HLK Element",
				"options": "Item"
			},
			{
				"fieldname": "total_independent_price",
				"fieldtype": "Check",
				"insert_after": "base_price_list_rate",
				"label": "Total Independent Price"
			},
			{
				"fieldname": "per_unit_price",
				"fieldtype": "Currency",
				"insert_after": "total_independent_price",
				"label": "Per Unit Price",
				"depends_on": "eval:doc.total_independent_price"
			},
			{
				"fieldname": "unit_description",
				"fieldtype": "Data",
				"insert_after": "per_unit_price",
				"label": "Unit Description",
				"depends_on": "eval:doc.total_independent_price"
			},
			{
				"fieldname": "do_not_show_discount",
				"fieldtype": "Check",
				"insert_after": "base_rate_with_margin",
				"label": "Do Not Show Discount"
			},
			{
				"fieldname": "variable_price",
				"fieldtype": "Check",
				"insert_after": "do_not_show_discount",
				"label": "Variable Price"
			}
		],
		"Sales Invoice": [
			{
				"fieldname": "introduction_template",
				"fieldtype": "Link",
				"insert_after": "scan_barcode",
				"label": "Introduction Template",
				"options": "HLK Text Template"
			},
			{
				"fieldname": "introduction",
				"fieldtype": "Text Editor",
				"insert_after": "introduction_template",
				"label": "Introduction"
			},
			{
				"fieldname": "deactivate_page_break",
				"fieldtype": "Check",
				"insert_after": "introduction",
				"label": "Deactivate Page Break"
			},
			{
				"fieldname": "hlk_structur_organisation",
				"fieldtype": "Table",
				"insert_after": "deactivate_page_break",
				"label": "HLK Structur Organisation",
				"options": "HLK Structur Organisation"
			},
			{
				"fieldname": "closing_text_template",
				"fieldtype": "Link",
				"insert_after": "items",
				"label": "Closing Text Template",
				"options": "HLK Text Template"
			},
			{
				"fieldname": "closing_text",
				"fieldtype": "Text Editor",
				"insert_after": "closing_text_template",
				"label": "Closing Text"
			},
			{
				"fieldname": "section_special_discounts",
				"fieldtype": "Section Break",
				"insert_after": "discount_amount",
				"label": "Special Discounts"
			},
			{
				"fieldname": "special_discounts",
				"fieldtype": "Table",
				"insert_after": "section_special_discounts",
				"label": "Special Discounts",
				"options": "HLK Discounts"
			}
		],
		"Sales Invoice Item": [
			{
				"fieldname": "hlk_element",
				"fieldtype": "Link",
				"insert_after": "item_code",
				"label": "HLK Element",
				"options": "Item"
			},
			{
				"fieldname": "total_independent_price",
				"fieldtype": "Check",
				"insert_after": "base_price_list_rate",
				"label": "Total Independent Price"
			},
			{
				"fieldname": "per_unit_price",
				"fieldtype": "Currency",
				"insert_after": "total_independent_price",
				"label": "Per Unit Price",
				"depends_on": "eval:doc.total_independent_price"
			},
			{
				"fieldname": "unit_description",
				"fieldtype": "Data",
				"insert_after": "per_unit_price",
				"label": "Unit Description",
				"depends_on": "eval:doc.total_independent_price"
			},
			{
				"fieldname": "do_not_show_discount",
				"fieldtype": "Check",
				"insert_after": "base_rate_with_margin",
				"label": "Do Not Show Discount"
			},
			{
				"fieldname": "variable_price",
				"fieldtype": "Check",
				"insert_after": "do_not_show_discount",
				"label": "Variable Price"
			}
		],
		"Sales Order": [
			{
				"fieldname": "introduction_template",
				"fieldtype": "Link",
				"insert_after": "scan_barcode",
				"label": "Introduction Template",
				"options": "HLK Text Template"
			},
			{
				"fieldname": "introduction",
				"fieldtype": "Text Editor",
				"insert_after": "introduction_template",
				"label": "Introduction"
			},
			{
				"fieldname": "deactivate_page_break",
				"fieldtype": "Check",
				"insert_after": "introduction",
				"label": "Deactivate Page Break"
			},
			{
				"fieldname": "hlk_structur_organisation",
				"fieldtype": "Table",
				"insert_after": "deactivate_page_break",
				"label": "HLK Structur Organisation",
				"options": "HLK Structur Organisation"
			},
			{
				"fieldname": "closing_text_template",
				"fieldtype": "Link",
				"insert_after": "items",
				"label": "Closing Text Template",
				"options": "HLK Text Template"
			},
			{
				"fieldname": "closing_text",
				"fieldtype": "Text Editor",
				"insert_after": "closing_text_template",
				"label": "Closing Text"
			},
			{
				"fieldname": "section_special_discounts",
				"fieldtype": "Section Break",
				"insert_after": "discount_amount",
				"label": "Special Discounts"
			},
			{
				"fieldname": "special_discounts",
				"fieldtype": "Table",
				"insert_after": "section_special_discounts",
				"label": "Special Discounts",
				"options": "HLK Discounts"
			}
		],
		"Sales Order Item": [
			{
				"fieldname": "hlk_element",
				"fieldtype": "Link",
				"insert_after": "customer_item_code",
				"label": "HLK Element",
				"options": "Item"
			},
			{
				"fieldname": "total_independent_price",
				"fieldtype": "Check",
				"insert_after": "base_price_list_rate",
				"label": "Total Independent Price"
			},
			{
				"fieldname": "per_unit_price",
				"fieldtype": "Currency",
				"insert_after": "total_independent_price",
				"label": "Per Unit Price",
				"depends_on": "eval:doc.total_independent_price"
			},
			{
				"fieldname": "unit_description",
				"fieldtype": "Data",
				"insert_after": "per_unit_price",
				"label": "Unit Description",
				"depends_on": "eval:doc.total_independent_price"
			},
			{
				"fieldname": "do_not_show_discount",
				"fieldtype": "Check",
				"insert_after": "base_rate_with_margin",
				"label": "Do Not Show Discount"
			},
			{
				"fieldname": "variable_price",
				"fieldtype": "Check",
				"insert_after": "do_not_show_discount",
				"label": "Variable Price"
			},
			{
				"fieldname": "amount_to_bill_now",
				"fieldtype": "Currency",
				"insert_after": "billed_amt",
				"label": "Amount To Bill Now"
			}
		]
	}
}
