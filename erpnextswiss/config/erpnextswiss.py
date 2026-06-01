from __future__ import unicode_literals
from frappe import _

def get_data():
    return[
        {
            "label": _("Bank & Zahlung"),
            "icon": "fa fa-money",
            "items": [
                   {
                       "type": "page",
                       "name": "bank_wizard",
                       "label": _("Bank-Assistent"),
                       "description": _("Bank-Assistent")
                   },
                   {
                       "type": "doctype",
                       "name": "Payment Proposal",
                       "label": _("Zahlungsvorschläge"),
                       "description": _("Zahlungsvorschläge")
                   },
                   {
                       "type": "doctype",
                       "name": "Direct Debit Proposal",
                       "label": _("Lastschriftvorschläge"),
                       "description": _("Lastschriftvorschläge")
                   },
                   {
                       "type": "doctype",
                       "name": "Payment Reminder",
                       "label": _("Mahnungen"),
                       "description": _("Mahnungen")
                   },
                   {
                       "type": "page",
                       "name": "bankimport",
                       "label": _("Bankimport"),
                       "description": _("Bankimport")
                   },
                   {
                       "type": "page",
                       "name": "match_payments",
                       "label": _("Zahlungen abgleichen"),
                       "description": _("Zahlungen abgleichen")
                   },
                   {
                       "type": "page",
                       "name": "payment_export",
                       "label": _("Zahlungsexport"),
                       "description": _("Zahlungsexport")
                   }
            ]
        },
        {
            "label": _("Steuern"),
            "icon": "fa fa-bank",
            "items": [
                   {
                       "type": "doctype",
                       "name": "VAT Declaration",
                       "label": _("MwSt-Abrechnung"),
                       "description": _("MwSt-Abrechnung")
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
            "label": _("Finanzen"),
            "icon": "fa fa-users",
            "items": [
                   {
                        "type": "report",
                        "name": "Account Sheets",
                        "label": _("Kontoblätter"),
                        "doctype": "GL Entry",
                        "is_query_report": True
                   }
            ]
        },
        {
            "label": _("Personal"),
            "icon": "fa fa-users",
            "items": [
                   {
                       "type": "doctype",
                       "name": "Salary Certificate",
                       "label": _("Lohnausweise"),
                       "description": _("Lohnausweise")
                   },
                   {
                        "type": "report",
                        "name": "Worktime Overview",
                        "label": _("Arbeitszeitübersicht"),
                        "doctype": "Timesheet",
                        "is_query_report": True
                   },
                   {
                        "type": "report",
                        "name": "Monthly Worktime",
                        "label": _("Monatliche Arbeitszeit"),
                        "doctype": "Timesheet",
                        "is_query_report": True
                   },
                   {
                        "type": "report",
                        "name": "Annual Salary Sheet",
                        "label": _("Jahreslohnzettel"),
                        "doctype": "Salary Slip",
                        "is_query_report": True
                   }
            ]
        },
        {
            "label": _("Verträge"),
            "icon": "octicon octicon-file-submodule",
            "items": [
                   {
                       "type": "doctype",
                       "name": "Contract",
                       "label": _("Verträge"),
                       "description": _("Verträge")
                   },
                   {
                        "type": "report",
                        "name": "Service Invoicing",
                        "label": _("Serviceverrechnung"),
                        "doctype": "Timesheet",
                        "is_query_report": True
                   },
                   {
                       "type": "doctype",
                       "name": "Specification Document",
                       "label": _("Spezifikationsdokumente"),
                       "description": _("Spezifikationsdokumente")
                   },
                   {
                       "type": "doctype",
                       "name": "Software Requirement",
                       "label": _("Softwareanforderungen"),
                       "description": _("Softwareanforderungen")
                   },
                   {
                       "type": "doctype",
                       "name": "Software Specification",
                       "label": _("Softwarespezifikationen"),
                       "description": _("Softwarespezifikationen")
                   }
            ]
        },
        {
            "label": _("Einstellungen"),
            "icon": "fa fa-bank",
            "items": [
                    {
                       "type": "doctype",
                       "name": "Label Printer",
                       "label": _("Etikettendrucker"),
                       "description": _("Etikettendrucker")
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
                       "label": _("App-Einstellungen"),
                       "description": _("App-Einstellungen")
                    },
                    {
                       "type": "doctype",
                       "name": "Worktime Settings",
                       "label": _("Arbeitszeiteinstellungen"),
                       "description": _("Arbeitszeiteinstellungen")
                    },
                    {
                       "type": "doctype",
                       "name": "BankImport Template",
                       "label": _("Bankimport-Vorlagen"),
                       "description": _("Bankimport-Vorlagen")
                    },
                    {
                       "type": "doctype",
                       "name": "VAT query",
                       "label": _("MwSt-Abfragen"),
                       "description": _("MwSt-Abfragen")
                    },
                    {
                       "type": "doctype",
                       "name": "Salary Certificate Settings",
                       "label": _("Lohnausweis-Einstellungen"),
                       "description": _("Lohnausweis-Einstellungen")
                    },
                    {
                       "type": "doctype",
                       "name": "ZUGFeRD Settings",
                       "label": _("ZUGFeRD-Einstellungen"),
                       "description": _("ZUGFeRD-Einstellungen")
                    }
            ]
        },
        {
            "label": _("Integrationen"),
            "icon": "octicon octicon-git-compare",
            "items": [
                    {
                       "type": "doctype",
                       "name": "ebics Connection",
                       "label": _("EBICS-Verbindungen"),
                       "description": _("EBICS-Verbindungen")
                    },
                    {
                       "type": "doctype",
                       "name": "ebics Statement",
                       "label": _("EBICS-Auszüge"),
                       "description": _("EBICS-Auszüge")
                    },
                    {
                       "type": "doctype",
                       "name": "ZUGFeRD Wizard",
                       "label": _("ZUGFeRD-Assistent"),
                       "description": _("ZUGFeRD-Assistent")
                    },
                    {
                       "type": "doctype",
                       "name": "Planzer Settings",
                       "label": _("Planzer-Einstellungen"),
                       "description": _("Planzer-Einstellungen")
                    },
                    {
                       "type": "doctype",
                       "name": "DPD Settings",
                       "label": _("DPD-Einstellungen"),
                       "description": _("DPD-Einstellungen")
                    },
                    {
                       "type": "doctype",
                       "name": "Datatrans Settings",
                       "label": _("Datatrans-Einstellungen"),
                       "description": _("Datatrans-Einstellungen")
                    },
                    {
                       "type": "doctype",
                       "name": "Payrexx Settings",
                       "label": _("Payrexx-Einstellungen"),
                       "description": _("Payrexx-Einstellungen")
                    },
                    {
                       "type": "doctype",
                       "name": "Worldline TIM",
                       "label": _("Worldline TIM"),
                       "description": _("Worldline TIM")
                    },
                    {
                       "type": "doctype",
                       "name": "GitLab Settings",
                       "label": _("GitLab"),
                       "description": _("GitLab")
                    },
                    {
                       "type": "doctype",
                       "name": "Mautic Settings",
                       "label": _("Mautic"),
                       "description": _("Mautic")
                    },
                    {
                       "type": "doctype",
                       "name": "Abacus Export File",
                       "label": _("Abacus-Exportdateien"),
                       "description": _("Abacus-Exportdateien")
                    },
                    {
                       "type": "page",
                       "name": "abacus_export",
                       "label": _("Abacus-Export"),
                       "description": _("Abacus-Export")
                    },
                    {
                       "type": "doctype",
                       "name": "CalDav Feed",
                       "label": _("CalDAV-Feed"),
                       "description": _("CalDAV-Feed")
                    }
            ]
        },
        {
            "label": _("EDI"),
            "icon": "octicon octicon-git-compare",
            "items": [
                   {
                       "type": "doctype",
                       "name": "EDI Connection",
                       "label": _("EDI-Verbindungen"),
                       "description": _("EDI-Verbindungen")
                   },
                   {
                       "type": "doctype",
                       "name": "EDI File",
                       "label": _("EDI-Dateien"),
                       "description": _("EDI-Dateien")
                   } ,
                   {
                       "type": "doctype",
                       "name": "EDI Sales Report",
                       "label": _("EDI-Verkaufsberichte"),
                       "description": _("EDI-Verkaufsberichte")
                   },
                   {
                        "type": "report",
                        "name": "EDI Sales Report Overview",
                        "label": _("EDI-Verkaufsbericht Übersicht"),
                        "doctype": "EDI Sales Report",
                        "is_query_report": True
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
                       "label": _("Tagesabschluss"),
                       "description": _("Tagesabschluss")
                   }
            ]
        },
        {
            "label": _("Qualität"),
            "icon": "octicon octicon-verified",
            "items": [
                   {
                       "type": "doctype",
                       "name": "Non Conformity Report 8D",
                       "label": _("8D-Fehlerbericht"),
                       "description": _("8D-Fehlerbericht")
                   },
                   {
                       "type": "doctype",
                       "name": "Inspection Equipment",
                       "label": _("Prüfmittel"),
                       "description": _("Prüfmittel")
                   },
                   {
                       "type": "doctype",
                       "name": "Inspection Equipment Transaction",
                       "label": _("Prüfmittelbewegungen"),
                       "description": _("Prüfmittelbewegungen")
                   },
                   {
                       "type": "doctype",
                       "name": "Inspection Equipment Type",
                       "label": _("Prüfmitteltypen"),
                       "description": _("Prüfmitteltypen")
                   },
                   {
                       "type": "doctype",
                       "name": "Calibration Test",
                       "label": _("Kalibrierung / Prüfung"),
                       "description": _("Kalibrierung / Prüfung")
                   },
                   {
                       "type": "doctype",
                       "name": "Calibration Test Set",
                       "label": _("Kalibrierung / Prüf-Set"),
                       "description": _("Kalibrierung / Prüf-Set")
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
                       "label": _("HLK-Einstellungen"),
                       "description": _("HLK-Einstellungen")
                   },
                {
                       "type": "doctype",
                       "name": "HLK Text Template",
                       "label": _("HLK-Textvorlagen"),
                       "description": _("HLK-Textvorlagen")
                   },
                {
                       "type": "doctype",
                       "name": "HLK Structur Organisation Template",
                       "label": _("HLK-Strukturvorlagen"),
                       "description": _("HLK-Strukturvorlagen")
                   },
                {
                       "type": "page",
                       "name": "bkp-importer",
                       "label": _("BKP-Import"),
                       "description": _("BKP-Import")
                   }
            ]
        }
]
