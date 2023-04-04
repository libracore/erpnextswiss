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
        
        if frappe.get_doc('Salary Certificate Settings').dynamic_config == 1:
            fetch_dynamic(self)
        else:
            fetch_static(self)

        return
 
# Old way for compatiblity  
def fetch_static(self):
    sql_query = """SELECT IFNULL(SUM(`tabSalary Slip`.`gross_pay`), 0) AS `gross`, IFNULL(SUM(`tabSalary Slip`.`net_pay`), 0) AS `net` 
        FROM `tabSalary Slip` 
        WHERE `tabSalary Slip`.`employee` = '{0}'
        AND `tabSalary Slip`.`posting_date` >= '{1}'
        AND `tabSalary Slip`.`posting_date` <= '{2}'
        AND `tabSalary Slip`.`docstatus` = 1;""".format(self.employee, self.start_date, self.end_date)
    values = frappe.db.sql(sql_query, as_dict=True)
    self.salary = get_component(self.employee, self.start_date, self.end_date, "B")
    self.gross_salary = values[0].gross
    self.net_salary = values[0].net
    self.deduction_ahv = (get_component(self.employee, self.start_date, self.end_date, "AHV") + 
        get_component(self.employee, self.start_date, self.end_date, "ALV") +
        get_component(self.employee, self.start_date, self.end_date, "NBUV"))
    self.deduction_pension = get_component(self.employee, self.start_date, self.end_date, "PK")   
        
    self.save()


def get_component(employee, start_date, end_date, component):
    sql_query = """SELECT `tabSalary Slip`.`employee`, IFNULL(SUM(`tabSalary Detail`.`amount`), 0) AS `amount`
        FROM `tabSalary Slip` 
        INNER JOIN `tabSalary Detail` ON `tabSalary Slip`.`name` = `tabSalary Detail`.`parent`
        WHERE `tabSalary Slip`.`employee` = '{0}'
        AND `tabSalary Slip`.`posting_date` >= '{1}'
        AND `tabSalary Slip`.`posting_date` <= '{2}'
        AND `tabSalary Slip`.`docstatus` = 1
        AND `tabSalary Detail`.`abbr` = '{3}';""".format(employee, start_date, end_date, component)
    values = frappe.db.sql(sql_query, as_dict=True)
    return values[0].amount

# new way to configure witch salary component is witch field in salary certificate

def fetch_dynamic(self):
    sql_query = """SELECT IFNULL(SUM(`tabSalary Slip`.`gross_pay`), 0) AS `gross`, IFNULL(SUM(`tabSalary Slip`.`net_pay`), 0) AS `net` 
        FROM `tabSalary Slip` 
        WHERE `tabSalary Slip`.`employee` = '{0}'
        AND `tabSalary Slip`.`posting_date` >= '{1}'
        AND `tabSalary Slip`.`posting_date` <= '{2}'
        AND `tabSalary Slip`.`docstatus` = 1;""".format(self.employee, self.start_date, self.end_date)
    values = frappe.db.sql(sql_query, as_dict=True)
   
    # Pos 1
    self.salary = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').salary)
    # Pos 2.1
    self.catering = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').catering)
    # Pos 2.2
    self.car = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').car)
    # Pos 2.3
    self.other_salary = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').other_salary)
    self.other_salary_description = frappe.get_doc('Salary Certificate Settings').other_salary_description
    # Pos 3
    self.irregular = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').irregular)
    self.irregular_description = frappe.get_doc('Salary Certificate Settings').irregular_description
    # Pos 4
    self.capital = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').capital)
    self.capital_description = frappe.get_doc('Salary Certificate Settings').capital_description
    # Pos 5
    self.participation = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').participation)
    # Pos 6
    self.board = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').board)
    # Pos 7
    self.other = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').other)
    self.other_description = frappe.get_doc('Salary Certificate Settings').other_description
    # Pos 8
    self.gross_salary = values[0].gross
    # Pos 9
    self.deduction_ahv = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').deduction_ahv)
    # Pos 10.1
    self.deduction_pension = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').deduction_pension)
    # Pos 10.2
    self.deduction_pension_additional = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').deduction_pension_additional)
    # Pos 11
    self.net_salary = values[0].net
    # Pos 12
    self.source_tax_deduction = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').source_tax_deduction)
    # Pos 13.1.1
    self.effective_expenses_travel = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').effective_expenses_travel)
    self.effective_expenses_travel_check = frappe.get_doc('Salary Certificate Settings').effective_expenses_travel_check
    # Pos 13.1.2
    self.effective_other_expenses = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').effective_other_expenses)
    self.effective_other_expenses_description = frappe.get_doc('Salary Certificate Settings').effective_other_expenses_description
    # Pos 13.2.1
    self.representation_expenses = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').representation_expenses)
    # Pos 13.2.2
    self.car_expenses = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').car_expenses)
    # Pos 13.2.3
    self.other_net_expenses = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').other_net_expenses)
    self.other_net_expenses_description = frappe.get_doc('Salary Certificate Settings').other_net_expenses_description
    # Pos 13
    self.education = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').education)
    # Pos 14
    self.other_salary_sides = frappe.get_doc('Salary Certificate Settings').other_salary_sides
    # Pos 15
    value = get_component_dynamic(self.employee, self.start_date, self.end_date, frappe.get_doc('Salary Certificate Settings').remarks)
    if value != 0.00:
        self.remarks = frappe.get_doc('Salary Certificate Settings').remark_prefix + "{:12.2f}".format(value)
    else:
        self.remarks = frappe.get_doc('Salary Certificate Settings').remark_prefix


    self.save()

 

def get_component_dynamic(employee, start_date, end_date, componentlist):
    
    if len(componentlist) == 0:
        return 0.0;

    expression = "";
    
    positiv = []
    negativ = []
    for item in componentlist:
        comp = frappe.get_doc("Salary Component", item.component)
        if item.is_negativ == 1:
            negativ.append(comp.name)
        else:
            positiv.append(comp.name)

    expression = "' OR `tabSalary Detail`.`salary_component` = '"

    pos = 0.0
    neg = 0.0

    if len(positiv) > 0:
        expression_pos = expression.join(positiv)

        sql_query_pos = """SELECT `tabSalary Slip`.`employee`, IFNULL(SUM(`tabSalary Detail`.`amount`), 0) AS `amount`
            FROM `tabSalary Slip` 
            INNER JOIN `tabSalary Detail` ON `tabSalary Slip`.`name` = `tabSalary Detail`.`parent`
            WHERE `tabSalary Slip`.`employee` = '{0}'
            AND `tabSalary Slip`.`posting_date` >= '{1}'
            AND `tabSalary Slip`.`posting_date` <= '{2}'
            AND `tabSalary Slip`.`docstatus` = 1
            AND (`tabSalary Detail`.`salary_component` = '{3}');""".format(employee, start_date, end_date, expression_pos)
        values = frappe.db.sql(sql_query_pos, as_dict=True)
        pos = values[0].amount
    
    if len(negativ) > 0:
        expression_neg = expression.join(negativ)

        sql_query_neg = """SELECT `tabSalary Slip`.`employee`, IFNULL(SUM(`tabSalary Detail`.`amount`), 0) AS `amount`
            FROM `tabSalary Slip` 
            INNER JOIN `tabSalary Detail` ON `tabSalary Slip`.`name` = `tabSalary Detail`.`parent`
            WHERE `tabSalary Slip`.`employee` = '{0}'
            AND `tabSalary Slip`.`posting_date` >= '{1}'
            AND `tabSalary Slip`.`posting_date` <= '{2}'
            AND `tabSalary Slip`.`docstatus` = 1
            AND (`tabSalary Detail`.`salary_component` = '{3}');""".format(employee, start_date, end_date, expression_neg)
        values = frappe.db.sql(sql_query_neg, as_dict=True)
        neg = values[0].amount
    return pos - neg