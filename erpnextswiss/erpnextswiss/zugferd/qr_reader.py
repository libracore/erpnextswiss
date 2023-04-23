# -*- coding: utf-8 -*-
# Copyright (c) 2018-2023, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
#

import fitz
import numpy as np
import cv2

@frappe.whitelist()
def find_qr_content(filename):
    qr_content = ""
    with fitz.Document(filename) as doc:
        for xref in {xref[0] for page in doc for xref in page.get_images(False) if xref[1] == 0}:
            # dictionary with image
            image_dict = doc.extract_image(xref)
            # image as OpenCV's Mat
            img = cv2.imdecode(np.frombuffer(image_dict["image"],
                                           np.dtype(f'u{image_dict["bpc"] // 8}')
                                           ),
                             cv2.IMREAD_GRAYSCALE)
            #cv2.imshow("OpenCV", i)
            #cv2.waitKey(0)
            detect = cv2.QRCodeDetector()
            value, points, straight_qr_code = detect.detectAndDecode(img)
            qr_content += value
    return qr_content
