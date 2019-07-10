# -*- coding: utf-8 -*-
# Copyright (c) 2018-2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

# try to get building number from address line
def get_building_number(address_line):
    parts = address_line.split(" ")
    if len(parts) > 1:
        return parts[-1]
    else:
        return ""
        
# get street name from address line
def get_street_name(address_line):
    parts = address_line.split(" ")
    if len(parts) > 1:
        return " ".join(parts[:-1])
    else:
        return address_line
        
# get pincode from address line
def get_pincode(address_line):
    parts = address_line.split(" ")
    if len(parts) > 1:
        return parts[0]
    else:
        return ""

# get city from address line
def get_city(address_line):
    parts = address_line.split(" ")
    if len(parts) > 1:
        return " ".join(parts[1:])
    else:
        return address_line

# adds Windows-compatible line endings (to make the xml look nice)    
def make_line(line):
    return line + "\r\n"
