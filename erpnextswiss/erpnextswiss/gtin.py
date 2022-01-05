# -*- coding: utf-8 -*-
# Copyright (c) 2018-2020, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe

class GTIN(object):    
    def __init__(self, barcode=''):
        self.barcode = barcode
    
    def __checkDigit(self, digits):
            total = sum(digits) + sum(list(map(lambda d: d*2, digits[-1::-2])))
            return (10 - (total % 10)) % 10
    
    def validateCheckDigit(self, barcode=''):
        barcode = (barcode if barcode else self.barcode)
        if len(barcode) in (8,12,13,14) and barcode.isdigit():
            digits = list(map(int, barcode))
            checkDigit = self.__checkDigit( digits[0:-1] )
            return checkDigit == digits[-1]
        return False
    
    def addCheckDigit(self, barcode=''):
        barcode = (barcode if barcode else self.barcode)
        if len(barcode) in (7,11,12,13) and barcode.isdigit():
            digits = list(map(int, barcode))
            return barcode + str(self.__checkDigit(digits))
        return ''

@frappe.whitelist()
def add_check_digit(code):
    return GTIN().addCheckDigit(code)
    
def test_gtin():
    # validateCheckDigit()
    gtin = GTIN()
    if gtin.validateCheckDigit('1'*11 +'7') == True:
        print('Pass')
    else:
        print('Fail')
    gtin = GTIN()
    if gtin.validateCheckDigit('1'*11 +'7') == True:
        print('Pass')
    else:
        print('Fail')
    if GTIN('1'*11 +'7').validateCheckDigit() == True:
        print('Pass')
    else:
        print('Fail')
    if GTIN().validateCheckDigit('1'*11 +'6') == False:
        print('Pass')
    else:
        print('Fail')
    
    # addCheckDigit()
    gtin = GTIN()
    if GTIN().addCheckDigit('1' *11) == '1'*11 +'7':
        print('Pass')
    else:
        print('Fail')
    gtin = GTIN('1'*7)
    if gtin.addCheckDigit() == '1'*7 +'5':
        print('Pass')
    else:
        print('Fail')
    if GTIN('1'*12).addCheckDigit() == '1'*12 +'6':
        print('Pass')
    else:
        print('Fail')
    if GTIN().addCheckDigit('1'*11) == '1'*11 + '7':
        print('Pass')
    else:
        print('Fail')
