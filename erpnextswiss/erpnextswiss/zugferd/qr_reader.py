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

@frappe.whitelist()
def find_qr_content_from_pdf(filename):
    codes = []
    
    # open PDF file
    pdf_file = fitz.open(filename)

    # get the number of pages in PDF file
    page_nums = len(pdf_file)

    # create empty list to store images information
    images_list = []

    # extract all images from each page
    for page_num in range(page_nums):
        page_content = pdf_file[page_num]
        images_list.extend(page_content.get_images())

    # raise error if PDF has no images
    if len(images_list)==0:
        raise ValueError('No images found in {0}'.format(filename))

    # save all the extracted images
    for i, img in enumerate(images_list, start=1):
        # extract the image object number
        xref = img[0]
        # extract image
        base_image = pdf_file.extract_image(xref)
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
