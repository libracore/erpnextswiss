# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
# Sync can be externally triggered by
#  $ bench execute erpnextswiss.erpnextswiss.ebics.sync --kwargs "{'debug': True}"
#  $ bench execute erpnextswiss.erpnextswiss.ebics.sync_connection --kwargs "{'connection': 'MyBank', 'debug': True}"
#

import frappe
from frappe.utils import add_days
from datetime import datetime

def sync(debug=False):
    if debug:
        print("Starting sync...")
    enabled_connections = frappe.get_all("ebics Connection", filters={'enable_sync': 1}, fields=['name'])
    if debug:
        print("Sync enabled for {0}".format(enabled_connections))
        
    for connection in enabled_connections:
        if debug:
            print("Syncing {0}".format(connection['name']))
        sync_connection(connection['name'], debug)
        
    if debug:
        print("Sync completed")
    return
            
def sync_connection(connection, debug=False):
    if not frappe.db.exists("ebics Connection", connection):
        print("Connection not found. Please check {0}.".format(connection) )
        return
        
    conn = frappe.get_doc("ebics Connection", connection)
    if not conn.synced_until:
        # try to sync last week
        date = add_days(datetime.today(), -7).date()
    else:
        date = add_days(conn.synced_until, 1)
    
    while date < datetime.today().date():
        if debug:
            print("Syncing {0}...".format(date.strftime("%Y-%m-%d")))
            
        conn.get_transactions(date.strftime("%Y-%m-%d"))
        # note: sync date update happens in the transaction record when there are results
        
        date = add_days(date, 1)
    
    return
