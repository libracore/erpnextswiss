# Copyright (c) 2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    
    return columns, data

def get_columns(filters):
    return [
        {"label": _("Account"), "fieldname": "account", "fieldtype": "Data", "width": 300},
        {"label": _("PY"), "fieldname": "py", "fieldtype": "Currency", "width": 100},
        {"label": _("Budget FY"), "fieldname": "budget", "fieldtype": "Currency", "width": 150},
        {"label": _("YTD"), "fieldname": "ytd", "fieldtype": "Currency", "width": 100},
        {"label": _("YTD %"), "fieldname": "ytd_percent", "fieldtype": "Percent", "width": 100},
        {"label": "", "fieldname": "blank", "fieldtype": "Data", "width": 20}
    ]
    
    
def get_data(filters):
    data_by_account = {}
    # get previous year
    date_parts = str(filters.date).split("-")
    py = int(date_parts[0]) - 1
    month_day = "-{0}-{1}".format(date_parts[1], date_parts[2])
    py_start = "{0}-01-01".format(py)
    py_end = "{0}{1}".format(py, month_day)
    # fetch data per account
    data = get_turnover(py_start, py_end, filters.company)
    for d in data:
        data_by_account[d['account']] = {
            'py': d['balance']
        }
        
    # year to date
    year = date_parts[0]
    ytd_start = "{0}-01-01".format(year)
    ytd_end = "{0}{1}".format(year, month_day)
    # fetch data per account
    data = get_turnover(ytd_start, ytd_end, filters.company)
    for d in data:
        if d['account'] not in data_by_account:
            # account was not used in PY, create a node
            data_by_account[d['account']] = {
                'py': 0
            }
        # update
        data_by_account[d['account']]['ytd'] = d['balance']

    # get budget values
    data = get_budget_fy(year, filters.company)
    for d in data:
        if d['account'] not in data_by_account:
            # account was not used in PY or YTD, create a node
            data_by_account[d['account']] = {
                'py': 0,
                'ytd': 0
            }
        # update
        data_by_account[d['account']]['budget_fy'] = d['amount']
    
    # convert to list
    output = []
    for k, v in sorted(data_by_account.items()):
        output.append({
            'account': k,
            'py': v['py'] if 'py' in v else 0,
            'ytd': v['ytd'] if 'ytd' in v else 0,
            'budget': v['budget_fy'] if 'budget_fy' in v else 0,
            'ytd_percent': (100 * (v['ytd'] if 'ytd' in v else 0) / v['budget_fy']) if 'budget_fy' in v else 0
        })
    
    return output

    
def get_turnover_budget_ytd(year, month, accounts, company):
    try:
        amount = frappe.db.sql("""SELECT 
                IFNULL(SUM(`tabMonthly Distribution Percentage`.`percentage_allocation` * `tabBudget Account`.`budget_amount` / 100), 0)
            FROM `tabBudget` 
            LEFT JOIN `tabMonthly Distribution Percentage` ON `tabMonthly Distribution Percentage`.`parent` = `tabBudget`.`monthly_distribution`
            LEFT JOIN `tabBudget Account` ON `tabBudget Account`.`parent` = `tabBudget`.`name`
            LEFT JOIN `tabAccount` ON `tabAccount`.`name` = `tabBudget Account`.`account`
            WHERE 
              `tabBudget`.`fiscal_year` = "{year}"
              AND `tabBudget`.`docstatus` < 2
              AND `tabBudget`.`company` = "{company}"
              AND `tabMonthly Distribution Percentage`.`idx` <= {month}
              AND `tabAccount`.`account_number` IN ({accounts});
                """.format(month=month, year=year, accounts=", ".join(accounts), 
                    last_day=last_day_of_month(year, month), company=company))[0][0]
    except:
        return 0
    return amount

def get_turnover(from_date, to_date, company):
    sql_query = """
       SELECT *, (`raw`.`credit` - `raw`.`debit`) AS `balance` 
       FROM
       (SELECT 
          `tabAccount`.`name` AS `account`, 
          /* IFNULL((SELECT 
             ROUND((SUM(`t1`.`debit`) - SUM(`t1`.`credit`)), 2)
           FROM `tabGL Entry` AS `t1`
           WHERE 
             `t1`.`posting_date` < '{from_date}'
            AND `t1`.`account` = `tabAccount`.`name`
          ), 0) AS `opening`, */
          IFNULL((SELECT 
             ROUND((SUM(`t3`.`debit`)), 2)
           FROM `tabGL Entry` AS `t3`
           WHERE 
             `t3`.`posting_date` <= '{to_date}'
             AND `t3`.`posting_date` >= '{from_date}'
            AND `t3`.`account` = `tabAccount`.`name`
          ), 0) AS `debit`,
          IFNULL((SELECT 
             ROUND((SUM(`t4`.`credit`)), 2)
           FROM `tabGL Entry` AS `t4`
           WHERE 
             `t4`.`posting_date` <= '{to_date}'
             AND `t4`.`posting_date` >= '{from_date}'
            AND `t4`.`account` = `tabAccount`.`name`
          ), 0) AS `credit`
       FROM `tabAccount`
       WHERE 
         `tabAccount`.`is_group` = 0
         AND `tabAccount`.`report_type` = "Profit and Loss"
         AND `tabAccount`.`company` = "{company}"
       ) AS `raw`
       WHERE (`raw`.`debit` - `raw`.`credit`) != 0;""".format(from_date=from_date, to_date=to_date, company=company)
 
    # run query
    data = frappe.db.sql(sql_query, as_dict = True)
    return data

def get_budget_fy(year, company):
    data = frappe.db.sql("""SELECT 
            `tabBudget Account`.`account` AS  `account`,
            IFNULL(`tabBudget Account`.`budget_amount`, 0) AS `amount`
        FROM `tabBudget Account` 
        LEFT JOIN `tabBudget` ON `tabBudget Account`.`parent` = `tabBudget`.`name`
        WHERE 
          `tabBudget`.`fiscal_year` = "{year}"
          AND `tabBudget`.`docstatus` < 2
          AND `tabBudget`.`company` = "{company}";
            """.format(year=year, company=company), as_dict=True)
    return data
