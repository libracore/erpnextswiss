# -*- coding: utf-8 -*-
# Copyright (c) 2017-2018, libracore and contributors
# License: AGPL v3. See LICENCE
#
# Execute with 
#    $ bench execute erpnextswiss.scripts.import_tools.import_items --args "['filename']"
#    $ bench execute erpnextswiss.scripts.import_tools.correct_weights --args "['filename']"
#    $ bench execute erpnextswiss.scripts.import_tools.load_images --args "['filename']"

# import definitions
from __future__ import unicode_literals
import frappe

# color config
BLUE = '\033[94m'
GREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'

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
ART_NR3=70
ART_NR4=71
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
LIE_MCODE=72		# brand code

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
	    print("Cells: {0}".format(len(cells)))
	    # check if item exists
	    print("Checking " + get_field(cells[ART_NR]))
	    update = False
	    
	    try:
		doc = frappe.get_doc("Item", get_field(cells[ART_NR]))
		update = True
		doc.cm_art_nr = "{0}.{1}.{2}.{3}".format(
			get_field(cells[ART_NR1]),
			get_field(cells[ART_NR2]),
			get_field(cells[ART_NR3]),
			get_field(cells[ART_NR4]))
		doc.basismat = "{0}".format(get_field(cells[ART_NR3]))
		doc.liemar = "{0}".format(get_field(cells[LIE_MCODE]))
		doc.save()
		print("Updated {0}".format(get_field(cells[ART_NR])))
	    except:
		# find supplier
		suppliers = frappe.get_all('Supplier', filters={'supplier_number': get_field(cells[ART_LIE_COD2])}, fields=['name'])	
		if suppliers:
			supplier = suppliers[0]['name']
		else:
			print("Supplier {0} not found".format(get_field(cells[ART_LIE_COD2])))
			supplier = None
		# create record
		doc = frappe.get_doc(
		    {
			"doctype":"Item", 
			"item_code": get_field(cells[ART_NR]),
			"item_name": get_field(cells[ART_BEZ]),
			"item_group": get_field(cells[ART_NR2]),
			"default_supplier": supplier,
			"supplier_items": [
			    {
				"supplier": supplier,
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
				"quality": "{0}-{1}".format(get_field(cells[ART_QUA1]), get_field(cells[ART_QU11])),
				"weight": get_field(cells[ART_GEW]),
				"count": get_field(cells[ART_ANZST1]),
				"unit": "ct"
			    },
			    {
				"element": "Edelstein",
				"material": get_field(cells[ART_BEZ2]),
				"quality": "{0}-{1}".format(get_field(cells[ART_QUA2]), get_field(cells[ART_QU12])),
				"weight": get_field(cells[ART_GEW]),
				"count": get_field(cells[ART_ANZST2]),
				"unit": "ct"
			    },
			    {
				"element": "Edelstein",
				"material": get_field(cells[ART_BEZ3]),
				"quality": "{0}-{1}".format(get_field(cells[ART_QUA3]), get_field(cells[ART_QU13])),
				"weight": get_field(cells[ART_GEW]),
				"count": get_field(cells[ART_ANZST3]),
				"unit": "ct"
			    },
			    {
				"element": "Edelstein",
				"material": get_field(cells[ART_BEZ4]),
				"quality": "{0}-{1}".format(get_field(cells[ART_QUA4]), get_field(cells[ART_QU14])),
				"weight": get_field(cells[ART_GEW]),
				"count": get_field(cells[ART_ANZST4]),
				"unit": "ct"
			    }
			]			
		    })
		# insert record
		print("{0}".format(doc.item_group))
		try:
			doc.insert()
			print("Inserted " + get_field(cells[ART_NR]))
		except:
			print("Inserting " + get_field(cells[ART_NR]) + " failed")
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

# loops through all items and applies the basis mat to the subtable
def apply_basismat():
	items = frappe.get_all('Item', filters={'disabled': 0}, fields=['name', 'basismat'])
	lookup = {
		'0': 'Edelstahl',
		'1': 'Stahl/Lederband',
		'2': 'Stahl/Stahlband',
		'3': 'Bicolor',
		'4': 'Bicolor/Lederband',
		'5': 'Bicolor/Metallband',
		'6': 'Stahl titanisiert',
		'7': 'Stahl-PVD-beschichtet',
		'8': 'Stahl mit 750 Gelbgold',
		'10': 'Titan',
		'11': 'Titan/Lederband',
		'12': 'Titan/Metallband',
		'13': 'Titan/Bicolor',
		'14': 'Titan/Bicolor/Lederband',
		'15': 'Titan/Bicolor/Metallband',
		'16': 'Titan/750 Gelbgold',
		'17': 'Diamant',
		'18': 'Carbon',
		'19': 'Zinn',
		'20': 'Plaqué',
		'21': 'Plaqué/Lederband',
		'22': 'Plaqué/Metallband',
		'23': 'Amerikaner',
		'24': 'vergoldet',
		'25': 'Nickel',
		'26': 'verchromt',
		'27': 'vernickelt',
		'28': 'rhodiniert',
		'29': 'versilbert',
		'30': '333 GG',
		'31': '333 WG',
		'32': '333 RG',
		'33': '333 bi',
		'34': 'Glas',
		'35': '375 GG',
		'36': '375 WG',
		'37': '375 RG',
		'38': '375 bicolor',
		'39': '375 Tri',
		'40': 'Hartmetall kratzfest',
		'41': 'Hartmetall/Lederband',
		'42': 'Hartmetall/Metallband',
		'43': 'H\'metall/H\'metallband',
		'44': 'H\'metall Bicolor',
		'45': 'H\'metall Bicolor/Lederbd',
		'46': 'H\'metall Bicolor/Met\'b.',
		'47': 'Messing',
		'48': 'Metall-Lackiert',
		'49': 'Leichtmetall',
		'50': '750 GG/Kautschuk',
		'51': '585 GG/Goldband',
		'52': '585 WG/Lederband',
		'53': '585 WG/Goldband',
		'54': 'Metall antiallergisch',
		'55': '585 GG',
		'56': '585 WG',
		'57': '585 RG',
		'58': '585 bi',
		'59': '585 Tri',
		'60': 'Keramik',
		'61': 'Keramik/Lederband',
		'62': 'Keramik/Metallband',
		'63': 'Keramik/Keramikband',
		'64': 'Porzellan',
		'65': 'Naturschiefer',
		'66': 'Kunststoff',
		'67': 'K\'stoff/K\'stoffband',
		'68': 'K\'stoff/Metallband',
		'69': 'Stahl/Gummiband',
		'70': '750 GG/Lederband',
		'71': '750 GG/Goldband',
		'72': '750 WG/Lederband',
		'73': '750 WG/Goldband',
		'74': '750 rh',
		'75': '750 GG',
		'76': '750 WG',
		'77': '750 RG',
		'78': '750 bicolor',
		'79': '750 tricolor',
		'80': '800 Silber',
		'81': '800 Silber vergoldet',
		'82': '800 Silber goldplattiert',
		'83': '800 Silber rh',
		'84': 'Zuchtperlen',
		'85': 'Süsswasserperlen',
		'86': 'Imit. Perlen',
		'87': 'Koralle',
		'88': '800 Silber/Lederband',
		'89': '800 Silber/Silberband',
		'90': '925 Silber',
		'91': '925 Silber vergoldet',
		'92': '925 Silber/Gold 750',
		'93': '925 Silber rh',
		'94': 'Palladium',
		'95': '950 Platin',
		'96': '950 Platin mit GG',
		'97': 'Holz',
		'98': '999.9 Gold',
		'99': '925 Silber/Silberband'
	}
	# loop through all active items
	for item in items:
	  print('.'),
	  # if there is a basismat, check child table
	  if item.basismat:
	    print('-'),
	    details = frappe.get_all('Item Detail', filters={'parent': item.name, 'element': 'Basismat'}, fields=['name'])
	    # prevent crashes due to missing entries
	    try:
	      # load all Basismat child entries
	      details = frappe.get_all('Item Detail', filters={'parent': item.name, 'element': 'Basismat'}, fields=['name'])
	      # if a child entry was found, load it
	      if details:
		print('>'),
		detail = frappe.get_doc('Item Detail', details[0]['name'])
		# if the detail contains no material, load it
		if not detail.material:
			print('o'),
			detail.material = lookup[item.basismat]
			detail.save()
			detail.submit()
			print("Item {0} updated with {1}".format(item.name, detail.material))
	    except:
		# do nothing
		pass

def correct_weights(filename):
    # read input file
    file = open(filename, "rU")
    data = file.read().decode('utf-8')
    rows = data.split(ROW_SEPARATOR)
    print("Rows: {0}".format(len(rows)))
    for i in range(1, len(rows)):
        cells = rows[i].split(CELL_SEPARATOR)

        if len(cells) > 1:
            print("Cells: {0}".format(len(cells)))
            # check if item exists
            print("Checking " + get_field(cells[ART_NR]))
            update_detail(get_field(cells[ART_NR]), "Edelstein", get_field(cells[ART_BEZ1]), get_field(cells[ART_GEW1]))
            update_detail(get_field(cells[ART_NR]), "Edelstein", get_field(cells[ART_BEZ2]), get_field(cells[ART_GEW2]))
            update_detail(get_field(cells[ART_NR]), "Edelstein", get_field(cells[ART_BEZ3]), get_field(cells[ART_GEW3]))
            update_detail(get_field(cells[ART_NR]), "Edelstein", get_field(cells[ART_BEZ4]), get_field(cells[ART_GEW4]))
    return

def update_detail(item_code, element, material, weight):
	matches = frappe.get_all('Item Detail', filters={'parent': item_code, 'element': element, 'material': material}, fields=['name'])
	if matches:
		doc = frappe.get_doc('Item Detail', matches[0]['name'])
		doc.weight = weight
		doc.save()
		print("Updated {0} {1} {2}".format(item_code, element, material))
	return

# read the length from the CM items
def read_length():
	matches = frappe.get_all('Item Detail', filters={'element': "Edelstein", 'material': "CM"}, fields=['parent', 'count'])
	if matches:
		for match in matches:
			doc = frappe.get_doc("Item", match['parent'])
			doc.length = match['count']
			doc.save()
			print("Updated {0} with {1} cm".format(match['parent'], match['count']))
	return

# load images from image link file
def load_images(filename):
    ITEM_CODE = None
    URL = None
    # read input file
    file = open(filename, "rU")
    data = file.read().decode('utf-8')
    rows = data.split(ROW_SEPARATOR)
    print("Rows: {0}".format(len(rows)))
    # find column definition
    cells = rows[0].split(CELL_SEPARATOR)
    for c in range(0, len(cells)):
        print(get_field(cells[c]).lower())
        if get_field(cells[c]).lower() == "item code":
            ITEM_CODE = c
        elif get_field(cells[c]).lower() == "url":
            URL = c
    if ITEM_CODE is None:
        print("ERROR: column 'item code' not found!")
        return
    if URL is None:
        print("ERROR: column 'url' not found!")
        return

    for i in range(1, len(rows)):
        cells = rows[i].split(CELL_SEPARATOR)

        if len(cells) > 1:
            # check if item exists
            print("Checking " + get_field(cells[ITEM_CODE]))
            matches = frappe.get_all("Item Supplier", filters={'supplier_part_no': get_field(cells[ITEM_CODE])}, fields=['parent'])
            if matches:
                item = frappe.get_doc("Item", matches[0]['parent'])
                item.image = get_field(cells[URL])
                item.save()
                print("Updated {0} ({1}) with {2}".format(get_field(cells[ITEM_CODE]),  matches[0]['parent'], get_field(cells[URL])))
    return

def import_pinv(filename):
    # read input file
    file = open(filename, "rU")
    data = file.read().decode('utf-8')
    rows = data.split(ROW_SEPARATOR)
    print("Rows: {0}".format(len(rows)))
    for i in range(1, len(rows)):
        #print(row)
        cells = rows[i].split(";")

        if len(cells) > 1:
            print("Cells: {0}".format(len(cells)))
            new_pinv = frappe.get_doc({
               'doctype': 'Purchase Invoice',
               'naming_series': cells[0],
               'posting_date': cells[1],
               'set_posting_time': 1,
               'company': cells[2],
               'total': cells[3],
               'items': [{
                  'item_code': cells[4],
                  'qty': cells[5],
                  'rate': cells[6]
               }],
               'discount_amount': float(cells[3]),
            })
            try:
                new_pinv.insert()
                new_pinv.submit()
                frappe.db.commit()
                print("Inserted {0}".format(cells[4]))
            except Exception as e:
                print(FAIL + "Error on item {0} ({1})".format(cells[4], e) + ENDC)
    file.close()
    return

def import_sinv(filename):
    # read input file
    file = open(filename, "rU")
    data = file.read().decode('utf-8')
    rows = data.split(ROW_SEPARATOR)
    print("Rows: {0}".format(len(rows)))
    for i in range(1, len(rows)):
        #print(row)
        cells = rows[i].split(";")

        if len(cells) > 1:
            print("Cells: {0}".format(len(cells)))
            new_sinv = frappe.get_doc({
               'doctype': 'Sales Invoice',
               'naming_series': cells[0],
               'posting_date': cells[1],
               'due_date': cells[1],
               'set_posting_time': 1,
               'company': cells[2],
               'currency': cells[3],
               'conversion_rate': cells[4],
               'selling_price_list': cells[5],
               'price_list_currency': cells[6],
               'plc_conversion_rate': cells[7],
               'base_net_total': float(cells[8]),
               'items': [{
                  'item_code': cells[9],
                  'qty': cells[10],
                  'rate': cells[11]
               }],
               'discount_amount': float(cells[8]),
               'debit_to': '1050 - Debitoren - MU'
            })
            try:
                new_sinv.insert()
                new_sinv.submit()
                frappe.db.commit()
                print("Inserted {0}".format(cells[9]))
            except Exception as e:
                print(FAIL + "Error on item {0} ({1})".format(cells[9], e) + ENDC)
    file.close()
    return

