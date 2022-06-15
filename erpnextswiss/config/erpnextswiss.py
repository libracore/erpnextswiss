from __future__ import unicode_literals
from frappe import _

def get_data():
    return[
        {
            "label": _("Banking"),
            "icon": "fa fa-money",
            "items": [
                   {
                       "type": "page",
                       "name": "bank_wizard",
                       "label": _("Bank Wizard"),
                       "description": _("Bank Wizard")
                   },
                   {
                       "type": "doctype",
                       "name": "Payment Proposal",
                       "label": _("Payment Proposal"),
                       "description": _("Payment Proposal")
                   },
                   {
                       "type": "doctype",
                       "name": "Direct Debit Proposal",
                       "label": _("Direct Debit Proposal"),
                       "description": _("Direct Debit Proposal")
                   },
                   {
                       "type": "doctype",
                       "name": "Payment Reminder",
                       "label": _("Payment Reminder"),
                       "description": _("Payment Reminder")
                   },
                   {
                       "type": "page",
                       "name": "bankimport",
                       "label": _("Bank import"),
                       "description": _("Bank import")
                   },
                   {
                       "type": "page",
                       "name": "match_payments",
                       "label": _("Match payments"),
                       "description": _("Match payments")
                   },
                   {
                       "type": "page",
                       "name": "payment_export",
                       "label": _("Payment export"),
                       "description": _("Payment export")
                   }
            ]
        },
        {
            "label": _("Taxes"),
            "icon": "fa fa-bank",
            "items": [
                   {
                       "type": "doctype",
                       "name": "VAT Declaration",
                       "label": _("VAT Declaration"),
                       "description": _("VAT Declaration")
                   },
                   {
                        "type": "report",
                        "name": "Kontrolle MwSt",
                        "label": _("Kontrolle MwSt"),
                        "doctype": "Sales Invoice",
                        "is_query_report": True
                    }
            ]
        },
        {
            "label": _("Finance"),
            "icon": "fa fa-users",
            "items": [
                   {
                        "type": "report",
                        "name": "Account Sheets",
                        "label": _("Account Sheets"),
                        "doctype": "GL Entry",
                        "is_query_report": True
                   }
            ]
        },
        {
            "label": _("Human Resources"),
            "icon": "fa fa-users",
            "items": [
                   {
                       "type": "doctype",
                       "name": "Salary Certificate",
                       "label": _("Salary Certificate"),
                       "description": _("Salary Certificate")
                   },
                   {
                        "type": "report",
                        "name": "Worktime Overview",
                        "label": _("Worktime Overview"),
                        "doctype": "Timesheet",
                        "is_query_report": True
                   },
                   {
                        "type": "report",
                        "name": "Monthly Worktime",
                        "label": _("Monthly Worktime"),
                        "doctype": "Timesheet",
                        "is_query_report": True
                   },
                   {
                        "type": "report",
                        "name": "Annual Salary Sheet",
                        "label": _("Annual Salary Sheet"),
                        "doctype": "Salary Slip",
                        "is_query_report": True
                   }
            ]
        },
        {
            "label": _("Contracts"),
            "icon": "octicon octicon-file-submodule",
            "items": [
                   {
                       "type": "doctype",
                       "name": "Contract",
                       "label": _("Contract"),
                       "description": _("Contract")                   
                   },
                   {
                       "type": "doctype",
                       "name": "Specification Document",
                       "label": _("Specification Document"),
                       "description": _("Specification Document")                   
                   },
                   {
                       "type": "doctype",
                       "name": "Software Requirement",
                       "label": _("Software Requirement"),
                       "description": _("Software Requirement")                   
                   },
                   {
                       "type": "doctype",
                       "name": "Software Specification",
                       "label": _("Software Specification"),
                       "description": _("Software Specification")                   
                   } 
            ]
        },
        {
            "label": _("Configuration"),
            "icon": "fa fa-bank",
            "items": [
                   {
                       "type": "doctype",
                       "name": "Label Printer",
                       "label": _("Label Printer"),
                       "description": _("Label Printer")                   
                   },
                   {
                       "type": "doctype",
                       "name": "Pincode",
                       "label": _("Pincode"),
                       "description": _("Pincode")                   
                   },
                   {
                       "type": "doctype",
                       "name": "ERPNextSwiss Settings",
                       "label": _("ERPNextSwiss Settings"),
                       "description": _("ERPNextSwiss Settings")                   
                   },
                   {
                       "type": "doctype",
                       "name": "Worktime Settings",
                       "label": _("Worktime Settings"),
                       "description": _("Worktime Settings")
                   },
                   {
                       "type": "doctype",
                       "name": "BankImport Template",
                       "label": _("BankImport Templates"),
                       "description": _("BankImport Templates")
                   },
                   {
                       "type": "doctype",
                       "name": "VAT query",
                       "label": _("VAT query"),
                       "description": _("VAT query")
                   }
            ]
        },
        {
            "label": _("Integrations"),
            "icon": "octicon octicon-git-compare",
            "items": [
                   {
                       "type": "doctype",
                       "name": "Abacus Export File",
                       "label": _("Abacus Export File"),
                       "description": _("Abacus Export File")                   
                   },
                   {
                       "type": "page",
                       "name": "abacus_export",
                       "label": _("Abacus Export"),
                       "description": _("Abacus Export")                   
                   }                 
            ]
        },
        {
            "label": _("POS"),
            "icon": "fa fa-money-bill",
            "items": [
                   {
                        "type": "doctype",
                       "name": "Daily Closing Statement",
                       "label": _("Daily Closing Statement"),
                       "description": _("Daily Closing Statement")                      
                   } 
			]
		},
		{
            "label": _("Quality"),
            "icon": "octicon octicon-verified",
            "items": [
                   {
                       "type": "doctype",
                       "name": "Non Conformity Report 8D",
                       "label": _("Non Conformity Report 8D"),
                       "description": _("Non Conformity Report 8D")                   
                   },
				   {
                       "type": "doctype",              
                       "name": "Inspection Equipment",
                       "label": _("Inspection Equipment"),
                       "description": _("Inspection Equipment")                   
                   },
				   {
                       "type": "doctype",
                       "name": "Inspection Equipment Transaction",
                       "label": _("Inspection Equipment Transaction"),
                       "description": _("Inspection Equipment Transaction")                   
                   },
				   {
                       "type": "doctype",
                       "name": "Inspection Equipment Type",
                       "label": _("Inspection Equipment Type"),
                       "description": _("Inspection Equipment Type")                   
                   },
				   {
                       "type": "doctype",
                       "name": "Calibration Test",
                       "label": _("Calibration / Test"),
                       "description": _("Calibration Test")                   
                   },
				   {
                       "type": "doctype",
                       "name": "Calibration Test Set",
                       "label": _("Calibration / Test-Set"),
                       "description": _("Calibration Test Set")                   
                   }
            ]
        },
        {
            "label": _("HLK"),
            "icon": "octicon octicon-file-submodule",
            "items": [
                   {
                       "type": "doctype",
                       "name": "HLK Settings",
                       "label": _("HLK Settings"),
                       "description": _("HLK Settings")                      
                   },
				   {
                       "type": "doctype",
                       "name": "HLK Text Template",
                       "label": _("HLK Text Template"),
                       "description": _("HLK Text Template")                      
                   },
				   {
                       "type": "doctype",
                       "name": "HLK Structur Organisation Template",
                       "label": _("HLK Structur Organisation Template"),
                       "description": _("HLK Structur Organisation Template")                      
                   },
				   {
                       "type": "page",
                       "name": "bkp-importer",
                       "label": _("BKP Importer"),
                       "description": _("BKP Importer")                      
                   } 
			]
		}
]
