# -*- coding: utf-8 -*-
# Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class SalaryCertificate(Document):
    # this function gathers values from the database
    def fetch_values(self):
        if not self.employee:
            frappe.msgprint( _("Please select a valid employee.") )
            return
        
        sql_query = """SELECT IFNULL(SUM(`gross_pay`), 0) AS `gross`, IFNULL(SUM(`net_pay`), 0) AS `net` FROM `tabSalary Slip` 
            WHERE `employee` = '{0}'
            AND `posting_date` >= '{1}'
            AND `posting_date` <= '{2}'""".format(self.employee, self.start_date, self.end_date)
        values = frappe.db.sql(sql_query, as_dict=True)
        self.salary = get_component(self.employee, self.start_date, self.end_date, "B")
        self.gross_salary = values[0].gross
        self.net_salary = values[0].net
        self.deduction_ahv = (get_component(self.employee, self.start_date, self.end_date, "AHV") + 
            get_component(self.employee, self.start_date, self.end_date, "ALV") +
            get_component(self.employee, self.start_date, self.end_date, "NBUV"))
        self.deduction_pension = get_component(self.employee, self.start_date, self.end_date, "PK")   
            
        self.save()
        return
    
def get_component(employee, start_date, end_date, component):
    sql_query = """SELECT `employee`, IFNULL(SUM(`tabSalary Detail`.`amount`), 0) AS `amount`
        FROM `tabSalary Slip` 
        INNER JOIN `tabSalary Detail` ON `tabSalary Slip`.`name` = `tabSalary Detail`.`parent`
        WHERE `employee` = '{0}'
        AND `posting_date` >= '{1}'
        AND `posting_date` <= '{2}'
        AND `abbr` = '{3}';""".format(employee, start_date, end_date, component)
    values = frappe.db.sql(sql_query, as_dict=True)
    return values[0].amount
