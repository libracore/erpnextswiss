# -*- coding: utf-8 -*-
# Copyright (c) 2018-2023, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
#

#import fitz # import error frontend
import numpy as np
import cv2
import frappe

@frappe.whitelist()
def find_qr_content(filename):
    qr_content = ""
    with fitz.Document(filename) as doc:
        for xref in {xref[0] for page in doc for xref in page.get_images(False) if xref[1] == 0}:
            # dictionary with image
            image_dict = doc.extract_image(xref)
            # image as OpenCV's Mat
            img = cv2.imdecode(np.frombuffer(image_dict["image"],
                                           np.dtype('u{0}'.format(image_dict["bpc"] // 8))
                                           ),
                             cv2.IMREAD_GRAYSCALE)
            #cv2.imshow("OpenCV", i)
            #cv2.waitKey(0)
            detect = cv2.QRCodeDetector()
            value, points, straight_qr_code = detect.detectAndDecode(img)
            qr_content += value
    return qr_content

#import cv2
import os
from wand.image import Image as wi

def find_qr_content2(filename):
    PDFfile = wi(filename=filename,resolution=400)
    Images = PDFfile.convert('png')
    ImageSequence = 1

    for img in PDFfile.sequence:
        Image = wi(image = img)
        Image.save(filename="/tmp/Image"+str(ImageSequence)+".png")
        ImageSequence += 1

    # read the QRCODE image
    image = cv2.imread("/tmp/Image1.png")
    # initialize the cv2 QRCode detector
    qrCodeDetector = cv2.QRCodeDetector()
    # detect and decode
    decodedText, points, straight_qrcode = qrCodeDetector.detectAndDecode(image)
    #points is the output array of vertices of the found QR code quadrangle
    #straight qrcode
    # if there is a QR code
    if points is not None:
        # QR Code detected handling code

        print('Decoded data: ' + decodedText)
        nrOfPoints = len(points)
        print('Number of points:  ' + str(nrOfPoints))
        points = points[0]
        for i in range(len(points)):
            pt1 = [int(val) for val in points[i]]
            pt2 = [int(val) for val in points[(i + 1) % 4]]
            cv2.line(image, pt1, pt2, color=(255, 0, 0), thickness=3)
      
        print('Successfully saved')
        cv2.imshow('Detected QR code', image)
        cv2.imwrite('Generated/extractedQrcode.png', image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("QR code not detected")
        # display the image with lines# length of bounding box


