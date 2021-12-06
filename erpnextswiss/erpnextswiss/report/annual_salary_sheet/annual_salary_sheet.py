# Copyright (c) 2021, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns, data = get_data(filters)
    return columns, data
    
def get_data(filters):
    # prepare columns
    columns = [
        {'fieldname': 'description', 'fieldtype': 'Data', 'label': _("Description"), 'width': 150}
    ]
    
    components = frappe.db.sql("""
        SELECT 
            `name`, 
            `salary_component_abbr` AS `abbr`
        FROM `tabSalary Component`
        WHERE `disabled` = 0
        ORDER BY `type` DESC;""", as_dict=True)
        
    from_date = frappe.get_value("Fiscal Year", filters.fiscal_year, "year_start_date")
    to_date = frappe.get_value("Fiscal Year", filters.fiscal_year, "year_end_date")
    
    # prepare rows
    data = []

    for c in components:
        data.append({'description': c['name'], 'auto': 1, 'total': 0})
    data.append({'description': _("Net Total"), 'auto': 0, 'total': 0})
    
    salary_slips = frappe.db.sql("""
        SELECT `name` 
        FROM `tabSalary Slip`
        WHERE `docstatus` = 1
          AND `employee` = "{employee}"
          AND `posting_date` >= "{from_date}"
          AND `posting_date` >= "{to_date}"
        ORDER BY `posting_date` ASC;""".format(employee=filters.employee, 
        from_date=from_date, to_date=to_date), as_dict=True)
    
    for s in range(0, len(salary_slips)):
        salary_slip = frappe.get_doc("Salary Slip", salary_slips[s]['name'])
        
        # extend columns
        columns.append({
            'fieldname': 'col{0}'.format(s), 
            'fieldtype': 'Currency', 
            'label': salary_slip.posting_date, 
            'width': 90
        })
                
        for e in salary_slip.earnings:
            for d in data:
                if d['description'] == e.salary_component:
                    d['col{0}'.format(s)] = e.amount
                    d['total'] += e.amount
                    break
        
        for u in salary_slip.deductions:
            for d in data:
                if d['description'] == u.salary_component:
                    d['col{0}'.format(s)] = (-1) * u.amount
                    d['total'] -= u.amount
                    break
        
        data[-1]['col{0}'.format(s)] = salary_slip.net_pay
        data[-1]['total'] += salary_slip.net_pay
    # extend columns
    columns.append({
        'fieldname': 'total', 
        'fieldtype': 'Currency', 
        'label': _("Total"), 
        'width': 90
    })
        
    return columns, data
