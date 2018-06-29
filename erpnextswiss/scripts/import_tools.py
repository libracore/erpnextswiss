# -*- coding: utf-8 -*-
# Copyright (c) 2017-2018, libracore and contributors
# License: AGPL v3. See LICENCE
#
# Execute with 
#    $ bench execute erpnextswiss.scripts.import_tools.import_items --args "['filename']"

# import definitions
from __future__ import unicode_literals
import frappe

# Parser config
ROW_SEPARATOR = "\n"
CELL_SEPARATOR = "\t"
# CSV column assignment
ART_NR=3        	# Item Code
ART_LIE_COD2=5  	# Link Supplier Verknüpfung zu Lieferant!
ART_BEST_NR=6   	# Artikelnummer für Lieferanten
ART_BEZ=7       	# Artikelname
ART_NR1=68		# Artikelgruppe (Hauptgruppe)
ART_NR2=69		# Artikelgruppe (Untergruppe)
ART_BEST_NR=6		# Artikelnummer für Lieferanten

ART_ANZST1=8		# Materialien:Edelstein (1. Zeile)  > Anzahl
ART_ANZST2=9		# Materialien:Edelstein (2. Zeile)  > Anzahl
ART_ANZST3=10		# Materialien:Edelstein (3. Zeile)  > Anzahl
ART_ANZST4=11		# Materialien:Edelstein (4. Zeile)  > Anzahl
ART_BEZ1=12		# Materialien: Edelstein (1. Zeile > Material) ausser wenn ‚CM‘, dann ist ART_ANZST1 = Länge in cm
ART_BEZ2=13		# Materialien: Edelstein (2. Zeile > Material)
ART_BEZ3=14		# Materialien: Edelstein (3. Zeile > Material)
ART_BEZ4=15		# Materialien: Edelstein (4. Zeile > Material)
ART_QUA1=16		# Materialien: Edelstein Qualität-Teil 1 (1. Zeile)
ART_QUA2=17		# Materialien: Edelstein Qualität-Teil 1 (2. Zeile)
ART_QUA3=18		# Materialien: Edelstein Qualität-Teil 1 (3. Zeile)
ART_QUA4=19		# Materialien: Edelstein Qualität-Teil 1 (2. Zeile)
ART_QU11=20		# Materialien: Edelstein Qualität-Teil 2 (1. Zeile)
ART_QU12=21		# Materialien: Edelstein Qualität-Teil 2 (2. Zeile)
ART_QU13=22		# Materialien: Edelstein Qualität-Teil 2 (3. Zeile)
ART_QU14=23		# Materialien: Edelstein Qualität-Teil 2 (4. Zeile)
ART_GEW1=24		# Materialien: Edelstein Gewicht (1. Zeile)
ART_GEW2=25		# Materialien: Edelstein Gewicht (2. Zeile)
ART_GEW3=26		# Materialien: Edelstein Gewicht (3. Zeile)
ART_GEW4=27		# Materialien: Edelstein Gewicht (4. Zeile)
ART_LEG1=37		# Materialien: Basismat > Qualität
ART_LEG2=38		# Materialien: Basismat > Material
ART_GEW=39		# Materialien: Basismat > Gewicht

ART_BEM1=55		# Beschreibung
ART_BEM2=56		# Beschreibung
ART_BEM3=57		# Beschreibung
ART_BEM4=58		# Beschreibung
ART_EKDAT=50		# Letztes Einkaufsdatum (?)
ART_VKDAT=51		# Letztes Verkaufsdatum (?)
ART_STK=52		# Anfangsbestand
ART_TOT=54		# Total Verkauft (?)


def import_items(filename):
    # read input file
    file = open(filename, "rU")
    data = file.read().decode('utf-8')
    rows = data.split(ROW_SEPARATOR)
    print("Rows: {0}".format(len(rows)))
    for i in range(1, len(rows)):
	#print(row)
	cells = rows[i].split(CELL_SEPARATOR)

	if len(cells) > 1:
	    # check if item exists
	    print("Checking " + get_field(cells[ART_NR]))
	    update = False
	    
	    try:
		doc = frappe.get_doc("Item", get_field(cells[ART_NR]))
		update = True
	    except:
		# find supplier
		supplier = frappe.get_all('Supplier', filters={'supplier_number': get_field(cells[ART_LIE_COD2])}, fields=['name'])	
		# create record
		doc = frappe.get_doc(
		    {
			"doctype":"Item", 
			"item_code": get_field(cells[ART_NR]),
			"item_name": get_field(cells[ART_BEZ]),
			"item_group": get_field(cells[ART_NR2]),
			"default_supplier": supplier[0]['name'],
			"supplier_items": [
			    {
				"supplier": supplier[0]['name'],
				"supplier_part_no": get_field(cells[ART_BEST_NR])
			    }	
			],
			"description": """{0}<br>{1}<br>{2}<br>{3}<br>
			    Letztes Einkaufsdatum: {4}<br>
			    Letztes Verkaufsdatum: {5}<br>
			    Anfangsbestand: {6}<br>
			    Total Verkauft: {7}""".format(
			    get_field(cells[ART_BEM1]),
			    get_field(cells[ART_BEM2]),
			    get_field(cells[ART_BEM3]),
			    get_field(cells[ART_BEM4]),
			    get_field(cells[ART_EKDAT]),
			    get_field(cells[ART_VKDAT]),
			    get_field(cells[ART_STK]),
			    get_field(cells[ART_TOT])),
			"is_stock_item": 1,
			"details": [
			    {
				"element": "Basismat",
				"material": get_field(cells[ART_LEG2]),
				"quality": get_field(cells[ART_LEG1]),
				"weight": get_field(cells[ART_GEW])
			    },
			    {
				"element": "Edelstein",
				"material": get_field(cells[ART_BEZ1]),
				"quality": get_field(cells[ART_QUA1]),
				"weight": get_field(cells[ART_GEW]),
				"count": get_field(cells[ART_ANZST1])
			    },
			    {
				"element": "Edelstein",
				"material": get_field(cells[ART_BEZ2]),
				"quality": get_field(cells[ART_QUA2]),
				"weight": get_field(cells[ART_GEW]),
				"count": get_field(cells[ART_ANZST2])
			    },
			    {
				"element": "Edelstein",
				"material": get_field(cells[ART_BEZ3]),
				"quality": get_field(cells[ART_QUA3]),
				"weight": get_field(cells[ART_GEW]),
				"count": get_field(cells[ART_ANZST3])
			    },
			    {
				"element": "Edelstein",
				"material": get_field(cells[ART_BEZ4]),
				"quality": get_field(cells[ART_QUA4]),
				"weight": get_field(cells[ART_GEW]),
				"count": get_field(cells[ART_ANZST4])
			    }
			]			
		    })
		# insert record
		doc.insert()
		print("Inserted " + get_field(cells[ART_NR]))
    return

# removes the quotation marks from a cell
def get_field(content):
	return content.replace("\"", "")

def test():
    doc = frappe.get_doc(
	{
	    "doctype":"Item", 
	    "item_code": "Test1",
	    "item_name": "Test1",
	    "item_group": "Products",
	    "supplier_items": [
		{
		    "supplier": "Test",
		    "supplier_part_no": "12345"
		}		
	    ]
		
	})
    doc.insert()
