# Copyright (c) 2021, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):

    # Role check is done by the system already
    #if not 'HR Manager' in frappe.get_roles(frappe.session.user):
    #    frappe.msgprint(_("Zugriff nur mit Rolle 'HR Manager'"), raise_exception=1)

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

    salary_slip_filters = {
      'docstatus': 1,
      'posting_date': ['between', (from_date, to_date)],
      'company': filters.company
    }
    if filters.employee:
      salary_slip_filters['employee'] = filters.employee;
    salary_slips = frappe.db.get_list("Salary Slip", salary_slip_filters, ['name'], order_by='posting_date')

    prev_posting_date = ''
    col_no = -1

    for s in range(0, len(salary_slips)):
        salary_slip = frappe.get_doc("Salary Slip", salary_slips[s]['name'])

        if salary_slip.posting_date != prev_posting_date:
            col_no += 1
            col_str = 'col{0}'.format(col_no)
            prev_posting_date = salary_slip.posting_date
            # extend columns
            columns.append({
                'fieldname': col_str,
                'fieldtype': 'Currency',
                'label': salary_slip.posting_date,
                'width': 90
            })

        for e in salary_slip.earnings:
            for d in data:
                if d['description'] == e.salary_component:
                    d[col_str] = d.get(col_str, 0) + e.amount
                    d['total'] += e.amount
                    break

        for u in salary_slip.deductions:
            for d in data:
                if d['description'] == u.salary_component:
                    d[col_str] = d.get(col_str, 0) - u.amount
                    d['total'] -= u.amount
                    break

        data[-1][col_str] = data[-1].get(col_str, 0) + salary_slip.net_pay
        data[-1]['total'] += salary_slip.net_pay

    columns.append({
        'fieldname': 'total',
        'fieldtype': 'Currency',
        'label': _("Total"),
        'width': 90
    })

    # remove empty rows
    if filters.suppress_empty_lines:
        clean_data =  []
        for d in data:
            if len(d.keys()) > 3: #description, total, auto
                clean_data.append(d)
    else:
        clean_data = data

    return columns, clean_data
