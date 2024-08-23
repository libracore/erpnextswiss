#-*- coding: utf-8 -*-

#  The MIT License (MIT)
#  
#  Copyright (c) 2014 Federal Office of Topography swisstopo, Wabern, CH and Aaron Schmocker 
#  
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#   of this software and associated documentation files (the "Software"), to deal
#   in the Software without restriction, including without limitation the rights
#   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#   copies of the Software, and to permit persons to whom the Software is
#   furnished to do so, subject to the following conditions:
#  
#  The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.
#  
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#   THE SOFTWARE.
# 

# WGS84 <-> LV03 converter based on the scripts of swisstopo written for python2.7
# Aaron Schmocker [aaron@duckpond.ch]
# Rewritten for Python 3.5 by libracore AG

# Source: http://www.swisstopo.admin.ch/internet/swisstopo/en/home/topics/survey/sys/refsys/projections.html (see PDFs under "Documentation")
# Updated 19 April 2021
# Please validate your results with NAVREF on-line service: http://www.swisstopo.admin.ch/internet/swisstopo/en/home/apps/calc/navref.html (difference ~ 1-2m)

# Updated 2024 by libracore AG to resolve elevation data (height above sea level)

import math
import frappe
import requests
from frappe.utils import flt

class GPSConverter(object):
    '''
    GPS Converter class which is able to perform convertions between the 
    CH1903 and WGS84 system.
    '''
    # Convert CH y/x/h to WGS height
    def CHtoWGSheight(self, y, x, h):
        # Axiliary values (% Bern)
        y_aux = (y - 600000) / 1000000
        x_aux = (x - 200000) / 1000000
        h = (h + 49.55) - (12.60 * y_aux) - (22.64 * x_aux)
        return h

    # Convert CH y/x to WGS lat
    def CHtoWGSlat(self, y, x):
        # Axiliary values (% Bern)
        y_aux = (y - 600000) / 1000000
        x_aux = (x - 200000) / 1000000
        lat = (16.9023892 + (3.238272 * x_aux)) + \
                - (0.270978 * pow(y_aux, 2)) + \
                - (0.002528 * pow(x_aux, 2)) + \
                - (0.0447 * pow(y_aux, 2) * x_aux) + \
                - (0.0140 * pow(x_aux, 3))
        # Unit 10000" to 1" and convert seconds to degrees (dec)
        lat = (lat * 100) / 36
        return lat

    # Convert CH y/x to WGS long
    def CHtoWGSlng(self, y, x):
        # Axiliary values (% Bern)
        y_aux = (y - 600000) / 1000000
        x_aux = (x - 200000) / 1000000
        lng = (2.6779094 + (4.728982 * y_aux) + \
                + (0.791484 * y_aux * x_aux) + \
                + (0.1306 * y_aux * pow(x_aux, 2))) + \
                - (0.0436 * pow(y_aux, 3))
        # Unit 10000" to 1" and convert seconds to degrees (dec)
        lng = (lng * 100) / 36
        return lng

    # Convert decimal angle (° dec) to sexagesimal angle (dd.mmss,ss)
    def DecToSexAngle(self, dec):
        degree = int(math.floor(dec))
        minute = int(math.floor((dec - degree) * 60))
        second = (((dec - degree) * 60) - minute) * 60
        return degree + (float(minute) / 100) + (second / 10000)
    
    # Convert sexagesimal angle (dd.mmss,ss) to seconds
    def SexAngleToSeconds(self, dms):
        degree = 0 
        minute = 0 
        second = 0
        degree = math.floor(dms)
        minute = math.floor((dms - degree) * 100)
        second = (((dms - degree) * 100) - minute) * 100
        return second + (minute * 60) + (degree * 3600)

    # Convert sexagesimal angle (dd.mmss) to decimal angle (degrees)
    def SexToDecAngle(self, dms):
        degree = 0
        minute = 0
        second = 0
        degree = math.floor(dms)
        minute = math.floor((dms - degree) * 100)
        second = (((dms - degree) * 100) - minute) * 100
        return degree + (minute / 60) + (second / 3600)
    
    # Convert Decimal Degrees to Seconds of Arc (seconds only of D°M'S").
    def DegToSec(self, angle):
        # Extract D°M'S".
        degree = int(angle)
        minute = int((angle - degree) * 100)
        second = (((angle - degree) * 100) - minute) * 100

        # Result in degrees sec (dd.mmss).
        return second + (minute * 60) + (degree * 3600)
    
    # Convert WGS lat/long (° dec) and height to CH h
    def WGStoCHh(self, lat, lng, h):
        lat = self.DecToSexAngle(lat)
        lng = self.DecToSexAngle(lng)
        lat = self.SexAngleToSeconds(lat)
        lng = self.SexAngleToSeconds(lng)
        # Axiliary values (% Bern)
        lat_aux = (lat - 169028.66) / 10000
        lng_aux = (lng - 26782.5) / 10000
        h = (h - 49.55) + (2.73 * lng_aux) + (6.94 * lat_aux)
        return h

    # Convert WGS lat/long (° dec) to CH x
    def WGStoCHx(self, lat, lng):
        lat = self.DecToSexAngle(lat)
        lng = self.DecToSexAngle(lng)
        lat = self.SexAngleToSeconds(lat)
        lng = self.SexAngleToSeconds(lng)
        # Axiliary values (% Bern)
        lat_aux = (lat - 169028.66) / 10000
        lng_aux = (lng - 26782.5) / 10000
        x = ((200147.07 + (308807.95 * lat_aux) + \
            + (3745.25 * pow(lng_aux, 2)) + \
            + (76.63 * pow(lat_aux,2))) + \
            - (194.56 * pow(lng_aux, 2) * lat_aux)) + \
            + (119.79 * pow(lat_aux, 3))
        return x

    # Convert WGS lat/long (° dec) to CH y
    def WGStoCHy(self, lat, lng):
        lat = self.DecToSexAngle(lat)
        lng = self.DecToSexAngle(lng)
        lat = self.SexAngleToSeconds(lat)
        lng = self.SexAngleToSeconds(lng)
        # Axiliary values (% Bern)
        lat_aux = (lat - 169028.66) / 10000
        lng_aux = (lng - 26782.5) / 10000
        y = (600072.37 + (211455.93 * lng_aux)) + \
            - (10938.51 * lng_aux * lat_aux) + \
            - (0.36 * lng_aux * pow(lat_aux, 2)) + \
            - (44.54 * pow(lng_aux, 3))
        return y

    def LV03toWGS84(self, east, north, height):
        '''
        Convert LV03 to WGS84 Return a array of double that contain lat, long,
        and height
        '''
        d = []
        d.append(self.CHtoWGSlat(east, north))
        d.append(self.CHtoWGSlng(east, north))
        d.append(self.CHtoWGSheight(east, north, height))
        return d
        
    def WGS84toLV03(self, latitude, longitude, ellHeight):
        '''
        Convert WGS84 to LV03 Return an array of double that contaign east,
        north, and height
        '''
        d = []
        d.append(self.WGStoCHy(latitude, longitude))
        d.append(self.WGStoCHx(latitude, longitude))
        d.append(self.WGStoCHh(latitude, longitude, ellHeight))
        return d

    def WGStoLV95North(self, lat, lng):
        # Converts Decimal Degrees to Sexagesimal Degree.
        lat = self.DecToSexAngle(lat)
        lng = self.DecToSexAngle(lng)
        # Convert Decimal Degrees to Seconds of Arc.
        phi = self.DegToSec(lat)
        lda = self.DegToSec(lng)

        # Calculate the auxiliary values (differences of latitude and longitude
        # relative to Bern in the unit[10000"]).
        phi_aux = (phi - 169028.66) / 10000
        lda_aux = (lda - 26782.5) / 10000

        # Process Swiss (MN95) North calculation.
        north = (1200147.07 + (308807.95 * phi_aux)) + \
          + (3745.25 * pow(lda_aux, 2)) + \
          + (76.63 * pow(phi_aux, 2)) + \
          - (194.56 * pow(lda_aux, 2) * phi_aux) + \
          + (119.79 * pow(phi_aux, 3))
        return north
    
    def WGSToLV95East(self, lat, lng): 
        # Converts Decimal Degrees to Sexagesimal Degree.
        lat = self.DecToSexAngle(lat)
        lng = self.DecToSexAngle(lng)
        # Convert Decimal Degrees to Seconds of Arc.
        phi = self.DegToSec(lat)
        lda = self.DegToSec(lng)

        # Calculate the auxiliary values (differences of latitude and longitude
        # relative to Bern in the unit[10000"]).
        phi_aux = (phi - 169028.66) / 10000
        lda_aux = (lda - 26782.5) / 10000

        # Process Swiss (MN95) East calculation.
        east = (2600072.37 + (211455.93 * lda_aux)) + \
          - (10938.51 * lda_aux * phi_aux) + \
          - (0.36 * lda_aux * pow(phi_aux, 2)) + \
          - (44.54 * pow(lda_aux, 3))
        return east
    
    def LV95ToWGSLatitude(self, east, north):
        # Convert the projection coordinates E (easting) and N (northing) in MN95
        # into the civilian system (Bern = 0 / 0) and express in the unit 1000 km.
        y_aux = (east - 2600000) / 1000000
        x_aux = (north - 1200000) / 1000000

        # Process latitude calculation.
        lat = (16.9023892 + (3.238272 * x_aux)) + \
          - (0.270978 * pow(y_aux, 2)) + \
          - (0.002528 * pow(x_aux, 2)) + \
          - (0.0447 * pow(y_aux, 2) * x_aux) + \
          - (0.0140 * pow(x_aux, 3))

        # Unit 10000" to 1" and converts seconds to degrees notation.
        lat = lat * 100 / 36
        return lat
        
    def LV95ToWGSLongitude(self, east, north): 
        # Convert the projection coordinates E (easting) and N (northing) in MN95
        # into the civilian system (Bern = 0 / 0) and express in the unit 1000 km.
        y_aux = (east - 2600000) / 1000000
        x_aux = (north - 1200000) / 1000000

        # Process longitude calculation.
        lng = (2.6779094 + (4.728982 * y_aux)) + \
          + (0.791484 * y_aux * x_aux) + \
          + (0.1306 * y_aux * pow(x_aux, 2)) + \
          - (0.0436 * pow(y_aux, 3))

        # Unit 10000" to 1" and converts seconds to degrees notation.
        lng = lng * 100 / 36
        return lng

@frappe.whitelist()
def get_swisstopo_url_from_gps(lat, lng, zoom=12, language="de"):
    converter = GPSConverter()
    y = int(converter.WGStoLV95North(lat, lng))
    x = int(converter.WGSToLV95East(lat, lng))
    url = get_swisstopo_url_from_ch(x, y, zoom, language)
    return url

@frappe.whitelist()
def get_swisstopo_url_from_ch(x, y, zoom=12, language="de"):
    url = "https://map.geo.admin.ch/?lang={language}&topic=ech&bgLayer=ch.swisstopo.swissimage&layers=ch.swisstopo.zeitreihen,ch.bfs.gebaeude_wohnungs_register,ch.bav.haltestellen-oev,ch.swisstopo.swisstlm3d-wanderwege&layers_opacity=1,1,1,0.8&layers_visibility=false,false,false,false&layers_timestamp=18641231,,,&E={x}&N={y}&zoom={zoom}".format(language=language, zoom=zoom, x=x, y=y)
    return url

@frappe.whitelist()
def get_swisstopo_url_from_pincode(pincode, zoom=12, language="de"):
    pins = frappe.get_all("Pincode", filters={'pincode': pincode}, fields=['name', 'latitude', 'longitude'])
    if pins and len(pins) > 0:
        url = get_swisstopo_url_from_gps(float(pins[0]['latitude'] or 0), float(pins[0]['longitude'] or 0), zoom, language)
    else:
        url = get_swisstopo_url_from_gps(47.4967528982669, 8.73430829109435, zoom, language)
    return url

@frappe.whitelist()
def get_height_above_sea_level(x, y):
    response = requests.get("https://api3.geo.admin.ch/rest/services/height?easting={x}&northing={y}".format(x=x, y=y))
    if response.status_code == 200:
        return flt(response.json().get('height'))
    else:
        return 0
    
@frappe.whitelist()
def get_height_above_sea_level_gps(lat, lng):
    converter = GPSConverter()
    y = int(converter.WGStoLV95North(lat, lng))
    x = int(converter.WGSToLV95East(lat, lng))
    elevation = get_height_above_sea_level(x, y)
    return elevation
