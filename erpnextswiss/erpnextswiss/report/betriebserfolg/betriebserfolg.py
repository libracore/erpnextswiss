# Copyright (c) 2013, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from dateutil.relativedelta import relativedelta
from frappe.utils import flt

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        {"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 250},
        {"label": _("YTD"), "fieldname": "ytd", "fieldtype": "Currency", "width": 120},
        {"label": _("PY"), "fieldname": "py", "fieldtype": "Currency", "width": 120},
        {"label": _("YTD %"), "fieldname": "ytd_percent", "fieldtype": "Percent", "width": 80},
        {"label": _("PY %"), "fieldname": "py_percent", "fieldtype": "Percent", "width": 80},
        {"label": _(""), "fieldname": "blank", "fieldtype": "Data", "width": 20}
    ]

def get_data(filters):
    # prepare periods
    ytd_from_date = frappe.get_cached_value("Fiscal Year", filters.get("fiscal_year"), 'year_start_date')
    ytd_to_date = frappe.get_cached_value("Fiscal Year", filters.get("fiscal_year"), 'year_end_date')
    py_from_date = ytd_from_date + relativedelta(years=-1)
    py_to_date = ytd_to_date - relativedelta(years=1)
    
    # fetch accounts
    accounts = frappe.db.sql("""
        SELECT `name`, `ebit_class`, `account_type`
        FROM `tabAccount`
        WHERE `disabled` = 0
          AND `is_group` = 0
          AND `company` = %(company)s
          AND `report_type` = "Profit and Loss"
          ORDER BY `name` ASC;
        """,
        {
            'company': filters.get('company')
        }, 
        as_dict=True
    )

    data = []
    
    revenue = {
        'ytd': 0,
        'py': 0
    }
    income = {
        'ytd': 0,
        'py': 0
    }
    # get revenue 1
    revenue_1 = {
        'ytd': 0,
        'py': 0
    }
    for a in accounts:
        if a.get("ebit_class") == "Betriebserfolg 1":
            _revenue = {
                'ytd': get_account_balance(a.get('name'), ytd_from_date, ytd_to_date),
                'py': get_account_balance(a.get('name'), py_from_date, py_to_date)
            }
            if _revenue.get('ytd') or _revenue.get('py'):
                data.append({
                    'description': a.get('name'),
                    'ytd': _revenue.get('ytd'),
                    'py': _revenue.get('py')
                })
                revenue_1['ytd'] += _revenue.get('ytd')
                revenue_1['py'] += _revenue.get('py')
                
                if a.get('account_type') == "Income Account":
                    income.update({
                        'ytd': income.get('ytd') + _revenue.get('ytd'),
                        'py': income.get('py') + _revenue.get('py')
                    })

    data.append({
        'description': "<b>{0}</b>".format(_("Betriebserfolg 1")),
        'ytd': revenue_1['ytd'],
        'py': revenue_1['py']
    })
    revenue.update({
        'ytd': revenue['ytd'] + revenue_1['ytd'],
        'py': revenue['py'] + revenue_1['py']
    })
    
    # get revenue 2
    revenue_2 = {
        'ytd': 0,
        'py': 0
    }
    for a in accounts:
        if a.get("ebit_class") == "Betriebserfolg 2":
            _revenue = {
                'ytd': get_account_balance(a.get('name'), ytd_from_date, ytd_to_date),
                'py': get_account_balance(a.get('name'), py_from_date, py_to_date)
            }
            if _revenue.get('ytd') or _revenue.get('py'):
                data.append({
                    'description': a.get('name'),
                    'ytd': _revenue.get('ytd'),
                    'py': _revenue.get('py')
                })
                revenue_2['ytd'] += _revenue.get('ytd')
                revenue_2['py'] += _revenue.get('py')
    revenue.update({
        'ytd': revenue['ytd'] + revenue_2['ytd'],
        'py': revenue['py'] + revenue_2['py']
    })
    data.append({
        'description': "<b>{0}</b>".format(_("Betriebserfolg 2")),
        'ytd': revenue['ytd'],
        'py': revenue['py']
    })
    
    # get revenue 3
    revenue_3 = {
        'ytd': 0,
        'py': 0
    }
    for a in accounts:
        if a.get("ebit_class") == "Betriebserfolg 3":
            _revenue = {
                'ytd': get_account_balance(a.get('name'), ytd_from_date, ytd_to_date),
                'py': get_account_balance(a.get('name'), py_from_date, py_to_date)
            }
            if _revenue.get('ytd') or _revenue.get('py'):
                data.append({
                    'description': a.get('name'),
                    'ytd': _revenue.get('ytd'),
                    'py': _revenue.get('py')
                })
                revenue_3['ytd'] += _revenue.get('ytd')
                revenue_3['py'] += _revenue.get('py')
    revenue.update({
        'ytd': revenue['ytd'] + revenue_3['ytd'],
        'py': revenue['py'] + revenue_3['py']
    })
    data.append({
        'description': "<b>{0}</b>".format(_("Betriebserfolg 3")),
        'ytd': revenue['ytd'],
        'py': revenue['py']
    })
    data.append({
        'description': "<b>{0}</b>".format(_("EBIT")),
        'ytd': revenue['ytd'],
        'py': revenue['py']
    })
    
    # get interest
    revenue_4 = {
        'ytd': 0,
        'py': 0
    }
    for a in accounts:
        if a.get("ebit_class") == "Interest":
            _revenue = {
                'ytd': get_account_balance(a.get('name'), ytd_from_date, ytd_to_date),
                'py': get_account_balance(a.get('name'), py_from_date, py_to_date)
            }
            if _revenue.get('ytd') or _revenue.get('py'):
                data.append({
                    'description': a.get('name'),
                    'ytd': _revenue.get('ytd'),
                    'py': _revenue.get('py')
                })
                revenue_4['ytd'] += _revenue.get('ytd')
                revenue_4['py'] += _revenue.get('py')
    revenue.update({
        'ytd': revenue['ytd'] + revenue_4['ytd'],
        'py': revenue['py'] + revenue_4['py']
    })
    data.append({
        'description': "<b>{0}</b>".format(_("Erfolg nach Zinsen")),
        'ytd': revenue['ytd'],
        'py': revenue['py']
    })
    
    # get taxes
    revenue_5 = {
        'ytd': 0,
        'py': 0
    }
    for a in accounts:
        if a.get("ebit_class") == "Tax":
            _revenue = {
                'ytd': get_account_balance(a.get('name'), ytd_from_date, ytd_to_date),
                'py': get_account_balance(a.get('name'), py_from_date, py_to_date)
            }
            if _revenue.get('ytd') or _revenue.get('py'):
                data.append({
                    'description': a.get('name'),
                    'ytd': _revenue.get('ytd'),
                    'py': _revenue.get('py')
                })
                revenue_5['ytd'] += _revenue.get('ytd')
                revenue_5['py'] += _revenue.get('py')
    revenue.update({
        'ytd': revenue['ytd'] + revenue_5['ytd'],
        'py': revenue['py'] + revenue_5['py']
    })
    data.append({
        'description': "<b>{0}</b>".format(_("Erfolg nach Steuern")),
        'ytd': revenue['ytd'],
        'py': revenue['py']
    })

    # add percent values
    for d in data:
        d['ytd_percent'] = (100 * d['ytd'] / income['ytd']) if income['ytd'] else 0
        d['py_percent'] = (100 * d['py'] / income['py']) if income['py'] else 0
    
    return data
    
def get_account_balance(account, from_date, to_date):
    amount = flt(
        frappe.db.sql("""
            SELECT IFNULL((SUM(`tabGL Entry`.`credit`) - SUM(`tabGL Entry`.`debit`)), 0)
            FROM `tabGL Entry` 
            WHERE 
                `tabGL Entry`.`posting_date` BETWEEN %(from_date)s AND %(to_date)s
                AND `tabGL Entry`.`account` = %(account)s
                AND `tabGL Entry`.`voucher_type` != "Period Closing Voucher";
            """,
            {
                'from_date': from_date,
                'to_date': to_date,
                'account': account
            },
            as_dict=False
            )[0][0]
        )
    return amount
