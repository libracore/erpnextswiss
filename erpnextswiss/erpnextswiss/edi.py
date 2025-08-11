# Copyright (c) 2022-2024, libracore and contributors
# For license information, please see license.txt
#
# This is the main EDI interaction file
#

from datetime import datetime
import frappe
import hashlib
from frappe.utils import cint
from frappe.desk.form.load import get_attachments
from datetime import datetime
from frappe import _

"""
Creates a new EDI File of PRICAT type
"""
def create_pricat(edi_connection):
    edi_con = frappe.get_doc("EDI Connection", edi_connection)
    edi_file = frappe.get_doc({
        'doctype': 'EDI File',
        'edi_connection': edi_connection,
        'edi_type': edi_con.edi_type,
        'date': datetime.now(),
        'title': "PRICAT - {0}".format(datetime.now())
    })
    edi_file.insert(ignore_permissions=True)
    frappe.db.commit()
    return edi_file.name
    
"""
Prepares the content of a PRICAT file for download
"""
def download_pricat(edi_file):
    edi = frappe.get_doc("EDI File", edi_file)
    edi_con = frappe.get_doc("EDI Connection", edi.edi_connection)
    price_list = frappe.get_doc("Price List", edi_con.price_list)
    
    content_segments = []
    # envelope
    content_segments.append(get_envelope(edi, edi_con))
    # message header
    content_segments.append(get_message_header(edi, edi_con))
    # beginning: price/sales catalogue number (hashed price list name, max. length 17)
    content_segments.append("BGM+9+{price_list}+9'".format(
        price_list=hashlib.md5((edi_con.price_list or "notdefined").encode('utf-8')).hexdigest()[:17]
    ))
    # ### SG1
    # message date
    content_segments.append(get_message_date(edi))
    ## date range placeholders
    content_segments.append("DTM+194:20000101:102'")
    content_segments.append("DTM+206:20991231:102'")
    
    # ### SG2
    # Reference
    content_segments.append("RFF+VA:{tax_id}'".format(
        tax_id=(frappe.get_value("Company", edi_con.company, "tax_id") or "").replace("-", "").replace(".", "")
    ))
    
    # buyer location number
    content_segments.append("NAD+BY+{gln_recipient}::9'".format(
        gln_recipient=edi_con.gln_recipient or ""
    ))

    # supplier location number
    content_segments.append("NAD+SU+{gln_sender}::9'".format(
        gln_sender=edi_con.gln_sender or ""
    ))
    
    # ### SG6
    # currency
    content_segments.append("CUX+2:{currency}:8'".format(
        currency=price_list.currency
    ))
    
    # ##### Price/Catalogue Detail Section
    # ### SG17
    
    # Product group information
    content_segments.append("PGI+3'")
    
    # ### SG36
    for item in edi.pricat_items:
        item_doc = frappe.get_doc("Item", item.item_code)
        # line item
        content_segments.append("LIN+{idx}+{action}+{gtin}:EN'".format(
            idx=item.idx,
            action=item.action.split("=")[0],
            gtin=item.gtin
        ))
        # internal item code
        content_segments.append("PIA+5+{item_code}:SA'".format(
            item_code=item.item_code[:35]
        ))
        # additional information
        content_segments.append("PIA+1+{item_group}:SA'".format(
            item_group=(item.item_group or "")[:35]
        ))
        # item group information
        item_group_doc = frappe.get_doc("Item Group", item.item_group)
        if item_group_doc.edi_gd_code:
            content_segments.append("PIA+1+{gd}:GD:BTE:9'".format(
                gd=(item_group_doc.edi_gd_code or "")[:35]
            ))
        # description
        content_segments.append("IMD+F+ANM+:::{item_name}:'".format(
            item_name=item.item_name
        ))
        # item group ~ article type
        content_segments.append("IMD+F+TPE+:::{item_group}:'".format(
            item_group=(item.item_group or "")[:35]
        ))
        # fabric (132, formerly U01)
        if edi_con.edi_format == "96A":
            code = "U01"
            fabric = (item_doc.get("fabric") or "")[:35].replace("+", ",")
        else:
            code = "132"
            fabric = (item_doc.get("fabric") or "").replace("+", ",")
        content_segments.append("IMD+F+{code}+:::{fabric}:'".format(
            code=code,
            fabric=fabric
        ))
        # brand
        content_segments.append("IMD+F+BRN+:::{brand}:'".format(
            brand=item_doc.get("brand") or ""
        ))
        # colour
        if item.colour:
            content_segments.append("IMD+F+35+:::{colour}:'".format(
                colour=item.colour or ""
            ))
        # size
        if item.size:
            content_segments.append("IMD+F+98+:::{size}:'".format(
                size=item.size or ""
            ))
        
        # quantity: minimum order
        content_segments.append("QTY+53:{min_qty}:{uom}'".format(
            min_qty=item.min_qty,
            uom=get_uom_code(get_edi_unit(edi_con, item_doc.get("stock_uom") or "PCE"))
        ))
        # quantity: qty per pack
        content_segments.append("QTY+52:{min_qty}:{uom}'".format(
            min_qty=item.qty_per_pack,
            uom=get_uom_code(get_edi_unit(edi_con, item_doc.get("stock_uom") or "PCE"))
        ))
        # availability date
        content_segments.append("DTM+44:20000101:102'")
        
        # price
        content_segments.append("PRI+AAA:{rate:.2f}:NTP'".format(
            rate=item.rate
        ))
        # recommended retail price
        content_segments.append("PRI+AAE:{retail_rate:.2f}:SRP'".format(
            retail_rate=item.retail_rate
        ))
        
        # currency
        content_segments.append("CUX+2:{currency}:8'".format(
            currency=price_list.currency
        ))
    # closing segment
    content_segments.append("UNT+{segment_count}+{name}'".format(
        segment_count=len(content_segments) + 1,
        name=edi.name
    ))
    content_segments.append("UNZ+{message_count}+{name}'".format(
        message_count=1,
        name=edi.name
    ))
    content = "\n".join(content_segments)
    return content

def get_uom_code(uom):
    if uom.lower() == "pair":
        return "PR"
    elif uom.lower() == "nos":
        return "PCE"
        
    else:
        # fallback to piece
        return "PCE"

# DESADV section

"""
Endpoint to hook delivery notes to DESADV
"""
@frappe.whitelist()
def check_create_desadv(delivery_note):
    # fetch delivery note
    dn = frappe.get_doc("Delivery Note", delivery_note)
    # check if there is a EDI connection for this customer
    desadv_connections = frappe.get_all("EDI Connection", 
        filters={'edi_type': 'DESADV', 'customer': dn.customer, 'disabled': 0}, 
        fields=['name'])
    if len(desadv_connections) > 0:
        desadv_file = create_desadv(desadv_connections[0]['name'], delivery_note)
        
"""
Creates a new EDI File of DESADV type
"""
def create_desadv(edi_connection, delivery_note):
    edi_con = frappe.get_doc("EDI Connection", edi_connection)
    edi_file = frappe.get_doc({
        'doctype': 'EDI File',
        'edi_connection': edi_connection,
        'edi_type': edi_con.edi_type,
        'date': datetime.now(),
        'title': "DESADV - {0}".format(datetime.now()),
        'delivery_note': delivery_note
    })
    edi_file.insert(ignore_permissions=True)
    edi_file.submit()
    frappe.db.commit()
    return edi_file.name
    
"""
Prepares the content of a PRICAT file for download
"""
def download_desadv(edi_file):
    edi = frappe.get_doc("EDI File", edi_file)
    edi_con = frappe.get_doc("EDI Connection", edi.edi_connection)
    delivery_note = frappe.get_doc("Delivery Note", edi.delivery_note)
    
    content_segments = []
    # envelope
    content_segments.append(get_envelope(edi, edi_con))
    # message header
    content_segments.append(get_message_header(edi, edi_con))
    # beginning: price/sales catalogue number (hashed price list name, max. length 17)
    content_segments.append("BGM+351+{delivery_note}+9'".format(
        delivery_note=edi.delivery_note[:35]
    ))
    # ### SG1
    # message date
    content_segments.append(get_message_date(edi))
    ## dispatch date
    content_segments.append("DTM+11:{year:04d}{month:02d}{day:02d}:102'".format(
        year=delivery_note.posting_date.year, month=delivery_note.posting_date.month, day=delivery_note.posting_date.day
    ))
    # reference: order number
    if delivery_note.po_no:
        content_segments.append("RFF+VN:{po_no}'".format(
            po_no=purify_string(delivery_note.po_no)
        ))
            
    # ### SG2
    # supplier location number
    content_segments.append("NAD+SU+{gln_sender}::9'".format(
        gln_sender=edi_con.gln_sender or ""
    ))
    
    # buyer location number - branch gln
    content_segments.append("NAD+BY+{gln_recipient}::9'".format(
        gln_recipient=frappe.get_value("Address", 
            (delivery_note.shipping_address_name or delivery_note.customer_address), "branch_gln") or ""
    ))
    # delivery party
    content_segments.append("NAD+DP+{gln_recipient}::9'".format(
        gln_recipient=frappe.get_value("Address", 
            (delivery_note.shipping_address_name or delivery_note.customer_address), "branch_gln") or ""
    ))
    # ultimate consignee
    content_segments.append("NAD+UC+{gln_recipient}::9'".format(
        gln_recipient=frappe.get_value("Address", 
            (delivery_note.shipping_address_name or delivery_note.customer_address), "branch_gln") or ""
    ))

    
    # ### SG10
    # consignment packaging sequence
    content_segments.append("CPS+1'")
    
    # ### SG11
    # packages
    content_segments.append("PAC+1'")
    
    # ### SG17 items
    for item in delivery_note.items:
        item_doc = frappe.get_doc("Item", item.item_code)
        # line item
        content_segments.append("LIN+{idx}++{gtin}:EN'".format(
            idx=item.idx,
            gtin=get_gtin(item_doc)
        ))
        # quantity
        content_segments.append("QTY+12:{qty}:{uom}'".format(
            qty=item.qty,
            uom=get_uom_code(get_edi_unit(edi_con, item_doc.get("stock_uom") or "PCE"))
        ))    

    # closing segment
    content_segments.append("UNT+{segment_count}+{name}'".format(
        segment_count=len(content_segments) + 1,
        name=edi.name
    ))
    content_segments.append("UNZ+{message_count}+{name}'".format(
        message_count=1,
        name=edi.name
    ))
    content = "\n".join(content_segments)
    return content

# segment functions
def get_envelope(edi, edi_con):
    return "UNB+{charset}:3+{gln_sender}:14+{gln_recipient}:14+{yy:02d}{mm:02d}{dd:02d}:{HH:02d}{MM:02d}+{name}+++++EANCOMREF 52+{test}'".format(
        charset=edi_con.charset,
        gln_sender=edi_con.gln_sender or "",
        gln_recipient=edi_con.gln_recipient or "",
        yy=int(str(edi.date.year)[2:4]),
        mm=edi.date.month,
        dd=edi.date.day,
        HH=edi.date.hour,
        MM=edi.date.minute,
        name=edi.name,
        test=cint(edi.test)
    )
    
def get_message_header(edi, edi_con):
    return "UNH+{name}+{edi_type}:D:{edi_format}:UN:{ean_version}'".format(
        name=edi.name,
        edi_type=edi.edi_type,
        edi_format=edi_con.edi_format,
        ean_version=edi_con.ean_version
    )

def get_message_date(edi):
    return "DTM+137:{year:04d}{month:02d}{day:02d}:102'".format(
        year=edi.date.year, month=edi.date.month, day=edi.date.day
    )

def get_gtin(item_doc):
    gtin = None
    for barcode in item_doc.barcodes:
        if barcode.barcode_type == "EAN":
            gtin = barcode.barcode
            break
    return gtin

def get_item_from_gtin(gtin):
    ean_matches = frappe.db.sql("""
        SELECT `parent`
        FROM `tabItem Barcode`
        WHERE `barcode_type` = "EAN"
          AND `barcode` = "{gtin}";
    """.format(gtin=gtin), as_dict=True)
    if len(ean_matches) > 0:
        return ean_matches[0]['parent']
    else:
        return None

def get_address_from_gln(gln):
    gln_matches = frappe.get_all("Address",
        filters={'branch_gln': gln},
        fields=['name'])
    if len(gln_matches) > 0:
        return gln_matches[0]['name']
    else:
        return None
"""
Inbound: monitor EDI files for incoming
"""
def process_incoming():
    incoming_files = frappe.db.sql("""
        SELECT `name`
        FROM `tabEDI File`
        WHERE `edi_type` IS NULL
          AND `docstatus` = 0;
    """, as_dict=True)
    
    for edi_file in incoming_files:
        # this is an inbound message: check communication
        communications = frappe.get_all("Communication", 
            filters={
                'reference_doctype': 'EDI File',
                'reference_name': edi_file['name']
            },
            fields=['name']
        )
        if len(communications) > 0:
            for c in communications:
                parse_communication(edi_file['name'], c['name'])
    return
        
"""
Inbound EDI message: parse communication and set file
"""
def parse_communication(edi_file, communication):
    edi = frappe.get_doc("EDI File", edi_file)
    comm = frappe.get_doc("Communication", communication)
    # fetch attachments
    attachments = get_attachments("Communication", communication)
    for a in attachments:
        f = frappe.get_doc("File", a['name'])
        content = f.get_content()
        # check if content has line feeds
        if content and not "\n" in content:
            content = content.replace("'", "'\n")
        edi.filename = f.file_name
        edi.content = content
        edi.save(ignore_permissions=True)
    
    # fallback: if no content was found from attachment, try to parse communication body
    if not edi.content:
        edi.content = comm.content
        edi.save(ignore_permissions=True)
        
    if "ORDERS" in edi.subject or "ORDERS" in edi.filename:
        edi.edi_type = "ORDERS"
        edi.save(ignore_permissions=True)
        create_orders(edi_file)
    elif "SLSRPT" in edi.subject or "SLSRPT" in edi.filename:
        edi.edi_type = "SLSRPT"
        edi.save(ignore_permissions=True)
        create_slsrpt(edi_file)
    
    return
    
"""
Creates a new EDI File of SLSRPT type
"""
def create_slsrpt(edi_file):
    edi = frappe.get_doc("EDI File", edi_file)
    # parse content
    segments = get_segments(edi.content)
    data = parse_edi(segments)
    
    # find matching connection
    edi_cons = frappe.get_all("EDI Connection", 
        filters={
            'edi_type': "SLSRPT",
            'gln_sender': data[0]['sender_gln'],
            'gln_recipient': data[0]['recipient_gln'],
            'disabled': 0
        },
        fields=['name']
    )
    if len(edi_cons) > 0:
        edi_con = frappe.get_doc("EDI Connection", edi_cons[0]['name'])
        edi.edi_connection = edi_cons[0]['name']
        edi.date = datetime.now()
        edi.save(ignore_permissions=True)
        
        # create sales report(s)
        for d in data:
            sales_report = frappe.get_doc({
                'doctype': "EDI Sales Report",
                'edi_file': edi_file,
                'customer': edi_con.customer,
                'date': d['document_date'],
                'currency': d['currency'],
                'location_gln': d['location_gln'],
                'address': get_address_from_gln(d['location_gln']),
                'title': "{0} - {1}".format(edi_con.customer, d['document_date'])
            })
            for item in d['items']:
                if item['location_gln']:
                    addresses = frappe.get_all("Address", filters={'branch_gln': item['location_gln']}, fields=['name'])
                    if len(addresses) > 0:
                        address = addresses[0]['name']
                    else:
                        address = None
                sales_report.append("items", {
                    'barcode': item['barcode'],
                    'item_code': item['item_code'],
                    'qty': item['qty'],
                    'rate': item['net_unit_rate'] if 'net_unit_rate' in item else 0,
                    'gln': item['location_gln'],
                    'address': address
                })
            sales_report.insert(ignore_permissions=True)
        edi.submit()
    else:
        frappe.log_error( _("No matching EDI Connection found for {0}").format(edi_file), _("Create EDI SLSRPT") )
    frappe.db.commit()
    return

"""
Creates a new EDI File of ORDERS type
"""
def create_orders(edi_file):
    edi = frappe.get_doc("EDI File", edi_file)
    # parse content
    segments = get_segments(edi.content)
    data = parse_edi(segments)
    # find matching connection
    edi_cons = frappe.get_all("EDI Connection", 
        filters={
            'edi_type': "ORDERS",
            'gln_sender': data[0]['sender_gln'] if 'sender_gln' in data[0] else data[0]['buyer'],
            'gln_recipient': data[0]['recipient_gln'] if 'recipient_gln' in data[0] else data[0]['supplier'],
            'disabled': 0
        },
        fields=['name']
    )
    if len(edi_cons) > 0:
        edi_con = frappe.get_doc("EDI Connection", edi_cons[0]['name'])
        edi.edi_connection = edi_cons[0]['name']
        edi.date = datetime.now()
        edi.save(ignore_permissions=True)
        
        # create sales order(s)
        for d in data:
            # set delivery date
            delivery_date = d['document_date']
            if 'requested_delivery_date' in d:
                delivery_date = d['requested_delivery_date']
            elif 'latest_delivery_date' in d:
                delivery_date = d['latest_delivery_date']
            elif 'earliest_delivery_date' in d:
                delivery_date = d['earliest_delivery_date']
                
            sales_order = frappe.get_doc({
                'doctype': "Sales Order",
                'edi_file': edi_file,
                'customer': edi_con.customer,
                'transaction_date': d['document_date'],
                'shipping_address_name': get_address_from_gln(d['deliver_to']),
                'delivery_date': delivery_date,
                'po_no': d['reference'],
                'territory': frappe.get_value("Customer", edi_con.customer, "territory"),
                'customer_group': frappe.get_value("Customer", edi_con.customer, "customer_group")
            })
            if 'currency' in data:
                sales_order.currency = d['currency']
            else:
                sales_order.currency = frappe.get_value("Customer", edi_con.customer, "default_currency")
            for item in d['items']:
                if item['item_code']:
                    sales_order.append("items", {
                        'item_code': item['item_code'],
                        'qty': item['qty'],
                        'rate': item['calculation_net_rate'] if 'calculation_net_rate' in item else item['net_unit_rate']
                    })
                else:
                    frappe.log_error( _("Order of unknown item: {0}: {1}").format(edi_file, item['barcode']), _("EDI create order") )
            sales_order.flags.ignore_mandatory = True
            sales_order.insert(ignore_permissions=True)
        edi.submit()
    else:
        frappe.log_error( _("No matching EDI Connection found for {0}").format(edi_file), _("Create EDI ORDERS") )
    frappe.db.commit()
    return
    
def get_segments(content):
    return content.split("\n")

def parse_segment(segment):
    structure = segment.split("+")
    matrix = []
    for s in structure:
        matrix.append(s.split(":"))
    return matrix

def parse_date(date_str, date_code):
    if date_code == "102" or date_code == "102'":
        return datetime.strptime(date_str, "%Y%m%d")
    else:
        return date_str
        
def parse_edi(segments):
    data = []
    location_gln = None
    sender_gln = None
    recipient_gln = None
    for segment in segments:
        structure = parse_segment(segment)
        if structure[0][0] == "UNB":
            # header
            sender_gln = structure[2][0]
            recipient_gln = structure[3][0]
        elif structure[0][0] == "UNH":
            # message header
            # create new file structure
            data.append({
                'items': []
            })
            data[-1]['edi_type'] = structure[2][0]
            #from UNB
            data[-1]['sender_gln'] = sender_gln
            data[-1]['recipient_gln'] = recipient_gln
        elif structure[0][0] == "BGM":
            # begin message
            try:
                data[-1]['reference'] = (structure[2][0] or "").replace("'", "")
                data[-1]['action'] = structure[3][0]
            except:
                data[-1]['action'] = 9          # default to add
        elif structure[0][0] == "DTM":
            # date
            if structure[1][0] == "137":        # document date
                data[-1]['document_date'] = parse_date(structure[1][1], structure[1][2])
            elif structure[1][0] == "90":        # report start date
                data[-1]['report_start_date'] = parse_date(structure[1][1], structure[1][2])
            elif structure[1][0] == "91":        # report end date
                data[-1]['report_end_date'] = parse_date(structure[1][1], structure[1][2])
            elif structure[1][0] == "2":        # requested delivery date
                data[-1]['requested_delivery_date'] = parse_date(structure[1][1], structure[1][2])
            elif structure[1][0] == "64":        # requested earliest delivery date
                data[-1]['earliest_delivery_date'] = parse_date(structure[1][1], structure[1][2])
            elif structure[1][0] == "63":        # requested latest delivery date
                data[-1]['latest_delivery_date'] = parse_date(structure[1][1], structure[1][2])
        elif structure[0][0] == "RFF":
            data[-1]['reference'] = (structure[1][1] or "").replace("'", "")
        elif structure[0][0] == "NAD":
            # name and address
            if structure[1][0] == "SU":        # supplier
                data[-1]['supplier'] = structure[2][0]
            elif structure[1][0] == "BY":        # buyer
                data[-1]['buyer'] = structure[2][0]
            elif structure[1][0] == "DP":        # delivery address
                data[-1]['deliver_to'] = structure[2][0]
        elif structure[0][0] == "CUX":
            # currencies
            data[-1]['currency'] = structure[1][1]
        elif structure[0][0] == "LOC":
            # location
            data[-1]['location_gln'] = structure[2][0]
            location_gln = structure[2][0]
        elif structure[0][0] == "LIN":
            # line item
            # find item
            item_barcode = structure[3][0]
            item_code = get_item_from_gtin(item_barcode)
            data[-1]['items'].append({
                'barcode': item_barcode,
                'item_code': item_code,
                'location_gln': location_gln            # apply last found location gln
            })
        elif structure[0][0] == "PRI":
            # price details
            if structure[1][0] == "AAA":
                data[-1]['items'][-1]['calculation_net_rate'] = float((structure[1][1] or "").replace("'", ""))
            elif structure[1][0] == "NTP":
                data[-1]['items'][-1]['net_unit_rate'] = float((structure[1][1] or "").replace("'", ""))
        elif structure[0][0] == "QTY":
            # quantity
            data[-1]['items'][-1]['qty'] = float(structure[1][1].split("'")[0])
        elif structure[0][0] == "UNT":
            # message trailer
            data[-1]['segments'] = structure[1][0]
    
    return data
    
def purify_string(s):
    return (s or "").replace("\r", "").replace("\n", "")
    
def get_edi_unit(edi_connection, unit):
    if type(edi_connection) == str:
        edi_connection = frappe.get_doc("EDI Connection", edi_connection)
    edi_unit = unit
    if edi_connection.units:
        for u in edi_connection.units:
            if u.system_unit == unit:
                edi_unit = u.edi_unit
                break
    return edi_unit
    
def get_system_unit(edi_connection, unit):
    if type(edi_connection) == str:
        edi_connection = frappe.get_doc("EDI Connection", edi_connection)
    system_unit = unit
    if edi_connection.units:
        for u in edi_connection.units:
            if u.edi_unit == unit:
                system_unit = u.system_unit
                break
    return system_unit
