# -*- coding: utf-8 -*-
# Copyright (c) 2018-2023, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
#

import fitz             # part of pymupdf (note: for Py3.5, use pymupdf==1.16.18)
import os
from PIL import Image
import cv2              # part of opencv-python
import numpy as np
import frappe
from frappe.utils import flt
from datetime import date

@frappe.whitelist()
def find_qr_content_from_pdf(filename):
    codes = []
    
    # open PDF file
    pdf_file = fitz.open(filename)

    # read by page
    for page in pdf_file:
        # get the page as image
        try:
            pix = page.get_pixmap(dpi=200)
        except:
            pix = page.getPixmap(matrix=fitz.Matrix(2, 2))                  # fall back to v1.16.18
        # cv2 reader
        qcd = cv2.QRCodeDetector()
        # get bytes array of image
        try:
            image_bytes = np.asarray(bytearray(pix.tobytes()), dtype="uint8")
        except:
            image_bytes = np.asarray(bytearray(pix.getImageData()), dtype="uint8")
        img = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        # add border to be able to detect it
        color = [255, 255, 255]
        top, bottom, left, right = [150]*4
        img_with_border = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)

        retval, decoded_info, points, straight_qrcode = qcd.detectAndDecodeMulti(img_with_border)

        if retval and len(decoded_info) > 0:
            code = decoded_info[0]
            codes.append(code)
    
    # if codes are found, you can leave here; otherwise, go to image-wise parsing
    if len(codes) > 0:
        return codes
    
    # get the number of pages in PDF file
    page_nums = len(pdf_file)

    # create empty list to store images information
    images_list = []

    # extract all images from each page
    for page_num in range(page_nums):
        page_content = pdf_file[page_num]
        try:
            images_list.extend(page_content.get_images())               # works with PyMuPDf v1.22.3
        except:
            try:
                images_list.extend(page_content.getImageList())         # fall back to v1.16.18
            except Exception as err:
                frappe.throw(err)

    # raise error if PDF has no images
    if len(images_list)==0:
        raise ValueError('No images found in {0}'.format(filename))

    # save all the extracted images
    for i, img in enumerate(images_list, start=1):
        # extract the image object number
        xref = img[0]
        # extract image
        try:
            base_image = pdf_file.extract_image(xref)
        except:
            try:
                base_image = pdf_file.extractImage(xref)                # fall back to v1.16.18
            except Exception as err:
                frappe.throw(err)
        # cv2 reader
        qcd = cv2.QRCodeDetector()
        # get bytes array of image
        image_bytes = np.asarray(bytearray(base_image['image']), dtype="uint8")
        img = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        # add border to be able to detect it
        color = [255, 255, 255]
        top, bottom, left, right = [150]*4
        img_with_border = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)

        retval, decoded_info, points, straight_qrcode = qcd.detectAndDecodeMulti(img_with_border)

        if retval and len(decoded_info) > 0:
            code = decoded_info[0]
            codes.append(code)
            
    return codes

"""
Extracts the relevant content for a purchase invoice from a QR code
:params:qr_content:     list of qr codes (text)
:return:                simplified dict with content
"""
def get_content_from_qr(qr_codes, default_tax, default_item):
    # dict for invoice
    invoice = {}
  
    # check format
    for code in qr_codes:
        if code.startswith("SPC"):
            invoice = read_swiss_qr(code, default_tax, default_item)
            return invoice
    
    return None
        
def read_swiss_qr(code, default_tax, default_item):
    invoice = {}
    
    code = code.replace("\r", "")          # remove windows line endings
    lines = code.split("\n")
    settings = frappe.get_doc("ERPNextSwiss Settings", "ERPNextSwiss Settings")
    
    if len(lines) > 30:
        invoice['supplier_name'] = lines[5]
        invoice['iban'] = lines[3] 
        invoice['supplier_al'] = lines[6]
        invoice['supplier_pincode'] = lines[8]
        invoice['supplier_city'] = lines[9]
        if not invoice['supplier_pincode'] or not invoice['supplier_city']:
            plz_city_parts = lines[7].split(" ")
            if not invoice['supplier_pincode']:
                invoice['supplier_pincode'] = plz_city_parts[0]
            if not invoice['supplier_city'] and len(plz_city_parts) > 1:
                invoice['supplier_city'] = " ".join(plz_city_parts[1:])
        country_matches = frappe.get_all("Country", filters={'code': lines[10].lower()}, fields=['name'])
        if len(country_matches) > 0:
            invoice['supplier_country'] = country_matches[0]['name']
        else:
            invoice['supplier_country'] = frappe.get_value("Global Defaults", "Global Defaults", "country")
        invoice['supplier_globalid'] = None
        supplier_match_by_iban = frappe.db.sql("""
            SELECT `name`, `tax_id`
            FROM `tabSupplier` 
            WHERE REPLACE(`iban`, " ", "") = "{iban}";""".format(iban=invoice['iban']), as_dict=True)
        if len(supplier_match_by_iban) > 0:
            # matched by tax id
            invoice['supplier'] = supplier_match_by_iban[0]['name']
            invoice['supplier_taxid'] = supplier_match_by_iban[0].get('tax_id')
        else:
            supplier_match_by_qriban = frappe.db.sql("""
                SELECT `name`, `tax_id` 
                FROM `tabSupplier` 
                WHERE REPLACE(`esr_participation_number`, " ", "") = "{iban}";""".format(iban=invoice['iban']), as_dict=True)
            if len(supplier_match_by_qriban) > 0:
                # matched by tax id
                invoice['supplier'] = supplier_match_by_qriban[0]['name']
                invoice['supplier_taxid'] = supplier_match_by_qriban[0].get('tax_id')
            else:
                supplier_match_by_name = frappe.get_all("Supplier", 
                                            filters={'supplier_name': invoice['supplier_name']},
                                            fields=['name'])   
                if len(supplier_match_by_name) > 0:
                    # matched by supplier name
                    invoice['supplier'] = supplier_match_by_name[0]['name']  
                    invoice['supplier_taxid'] = supplier_match_by_name[0].get('tax_id')
                else:
                    # need to insert new supplier
                    invoice['supplier'] = None
                    invoice['supplier_taxid'] = None
                
        # posting date not provided by QR: use default as date
        today = date.today()
        invoice['posting_date'] = today.strftime("%Y-%m-%d")
        invoice['due_date'] = today.strftime("%Y-%m-%d")
        
        invoice['terms'] = lines[29]
        invoice['esr_reference'] = lines[28]
        invoice['doc_id'] = lines[28]
         
        invoice['currency'] = lines[19]
        
        tax_template = frappe.get_doc("Purchase Taxes and Charges Template", default_tax)
        if len(tax_template.taxes) > 0:
            tax_rate = tax_template.taxes[0].rate
        else:
            tax_rate = 0    
            # default is not applicable: settings.scanning_default_tax_rate or 7.7, use no tax
        invoice['tax_rate'] = tax_rate
        invoice['tax_template'] = default_tax
        
        grand_total = flt(lines[18])
        net_total = round(grand_total / ((100 + tax_rate)/100), 2)
        
        invoice['line_total'] = net_total
        invoice['total_taxes'] = grand_total - net_total
        invoice['grand_total'] = grand_total
        
        # try to fetch a default item from the supplier
        if frappe.db.exists("Supplier", invoice['supplier']):
            supplier_item = frappe.get_doc("Supplier", invoice['supplier']).get('default_item')
            if supplier_item:
                default_item = supplier_item
                
        # collect items: not provided by QR
        invoice['items'] = [
            {
                'net_price': net_total,
                'qty': 1,
                'seller_item_code': None,
                'item_name': frappe.get_cached_value("Item", default_item, "item_name"),
                'item_code': default_item
            }
        ]
        
        return invoice
        
    else:
        return None
    
