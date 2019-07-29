# -*- coding: utf-8 -*-
# Copyright (c) 2018-2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt


import frappe
from frappe import _

# send newsletter with dynamic content
@frappe.whitelist()
def create_zugferd_xml(sales_invoice):
    doc=frappe.get_doc("Sales Invoice", sales_invoice)
    
    frappe.msgprint("Tes {0}".format(doc.customer_name))
   
    return
    
def generate_zugferd_pdf():
    
# get xml via method of austrian vat, method added below, needs to be adapted to sinv datastructur, actual dowload of xml is a js file, how to handle that.
   
    xml = generate_transfer_file(self)
    
# get pdf from frappe/sinv
    sinv = frappe.get_doc("Sales Invoice", sales_invoice)
    
# get acces to sinv html with one of these two
    sinvHtml = frappe.get_value("Sales Invoice", sales_invoice, html)
    html = sinv.html
    
    from frappe.utils.pdf import get_pdf
    pdf = get_pdf(sinvHtml)   # input should be html
    
    
    
    
    
    
     
# generate zugferdPdf
    from erpnextswiss.erpnextswiss.facturx import generate_facturx_from_binary
    facturxPDF = generate_facturx_from_binary(pdf, xml)
    
 
    return facturxPDF



# generate xml export
# ToDO: adapt to sinv datastruktur
def generate_transfer_file(self):
    #try:        
    # create xml header
    content = make_line("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
    # define xml root node
    content += make_line("<ERKLAERUNGS_UEBERMITTLUNG>")
    content += make_line(" <INFO_DATEN>")
    content += make_line("  <ART_IDENTIFIKATIONSBEGRIFF>FASTNR</ART_IDENTIFIKATIONSBEGRIFF>")
    fastnr = frappe.get_value("ERPNextAustria Settings", "ERPNextAustria Settings", "fastnr")
    content += make_line("  <IDENTIFIKATIONSBEGRIFF>{0}</IDENTIFIKATIONSBEGRIFF>".format(fastnr))
    content += make_line("  <PAKET_NR>1</PAKET_NR>")
    now = datetime.now()
    content += make_line("  <DATUM_ERSTELLUNG type=\"datum\">{0:04d}-{1:02d}-{2:02d}</DATUM_ERSTELLUNG>".format(now.year, now.month, now.day))
    content += make_line("  <UHRZEIT_ERSTELLUNG type=\"uhrzeit\">{0:02d}:{1:02d}:{2:02d}</UHRZEIT_ERSTELLUNG>".format(now.hour, now.minute, now.second))
    content += make_line("  <ANZAHL_ERKLAERUNGEN>1</ANZAHL_ERKLAERUNGEN>")
    content += make_line(" </INFO_DATEN>")
    content += make_line(" <ERKLAERUNG art=\"U30\">")
    content += make_line("  <SATZNR>1</SATZNR>")
    content += make_line("  <ALLGEMEINE_DATEN>")
    content += make_line("   <ANBRINGEN>U30</ANBRINGEN>")
    content += make_line("   <ZRVON type=\"jahrmonat\">{0}</ZRVON>".format(self.start_date[0:7]))
    content += make_line("   <ZRBIS type=\"jahrmonat\">{0}</ZRBIS>".format(self.end_date[0:7]))
    content += make_line("   <FASTNR>{0}</FASTNR>".format(fastnr))
    content += make_line("   <KUNDENINFO>{0}</KUNDENINFO>".format(self.company))
    content += make_line("  </ALLGEMEINE_DATEN>")
    content += make_line("  <LIEFERUNGEN_LEISTUNGEN_EIGENVERBRAUCH>")
    content += make_line("   <KZ000 type=\"kz\">{0:.2f}</KZ000>".format(self.revenue))
    content += make_line("   <STEUERFREI>")
    content += make_line("    <KZ011 type=\"kz\">{0:.2f}</KZ011>".format(self.exports))
    content += make_line("    <KZ017 type=\"kz\">{0:.2f}</KZ017>".format(self.inner_eu))
    content += make_line("   </STEUERFREI>")
    content += make_line("   <KZ021 type=\"kz\">{0:.2f}</KZ021>".format(self.receiver_vat))
    content += make_line("   <VERSTEUERT>")
    content += make_line("    <KZ022 type=\"kz\">{0:.2f}</KZ022>".format(self.amount_normal))
    content += make_line("    <KZ029 type=\"kz\">{0:.2f}</KZ029>".format(self.reduced_amount))
    content += make_line("    <KZ057 type=\"kz\">{0:.2f}</KZ057>".format(self.tax_057))
    content += make_line("   </VERSTEUERT>")
    content += make_line("  </LIEFERUNGEN_LEISTUNGEN_EIGENVERBRAUCH>")
    content += make_line("  <VORSTEUER>")
    content += make_line("   <KZ060 type=\"kz\">{0:.2f}</KZ060>".format(self.total_pretax))
    content += make_line("   <KZ061 type=\"kz\">{0:.2f}</KZ061>".format(self.import_pretax))
    content += make_line("   <KZ083 type=\"kz\">{0:.2f}</KZ083>".format(self.import_charge_pretax))
    content += make_line("   <KZ065 type=\"kz\">{0:.2f}</KZ065>".format(self.intercommunal_pretax))
    content += make_line("   <KZ066 type=\"kz\">{0:.2f}</KZ066>".format(self.taxation_pretax))
    content += make_line("  </VORSTEUER>")
    content += make_line("  <INNERGEMEINSCHAFTLICHE_ERWERBE>")
    content += make_line("   <KZ070 type=\"kz\">{0:.2f}</KZ070>".format(self.intercommunal_revenue))
    content += make_line("   <VERSTEUERT_IGE>")
    content += make_line("    <KZ072 type=\"kz\">{0:.2f}</KZ072>".format(self.amount_inter_normal))
    content += make_line("   </VERSTEUERT_IGE>")
    content += make_line("  </INNERGEMEINSCHAFTLICHE_ERWERBE>")
    content += make_line(" </ERKLAERUNG>")
    content += make_line("</ERKLAERUNGS_UEBERMITTLUNG>")
     
    return { 'content': content }
#except IndexError:
#    frappe.msgprint( _("Please select at least one payment."), _("Information") )
#    return
#except:
#    frappe.throw( _("Error while generating xml. Make sure that you made required customisations to the DocTypes.") )
#    return

# adds Windows-compatible line endings (to make the xml look nice)    
def make_line(line):
    return line + "\r\n"

