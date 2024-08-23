// this function checks if an ESR code is valid
function check_esr(esr_raw) {
    esr_code = esr_raw.replace(/ /g, '');
    // define algo
    alg = new Array (0,9,4,6,8,2,7,1,3,5);
    // convert esr code into array form
    esr_array = esr_code.split("");
    // preset remainder R2
    R2 = 0;
    // loop through digites except check digit
    for ( i = 0; i < (esr_code.length - 1); i++ ) {
        // get remainder plus next digit
        Rpr = parseInt(R2) + parseInt(esr_array[i]);
        // modulo 10 from algo
        R2 = alg[Rpr % 10];
    }
    // check digit
    P2 = (10 - R2) % 10;
    if (parseInt(esr_array[esr_array.length - 1]) == P2) {
        return true;
    } else {
        return false;
    }
}

// this function computes the ESR reference and code for a sales invoice
function esr_sales_invoice(frm, participant_number) {
    alg = new Array (0,9,4,6,8,2,7,1,3,5);    // vorgebener Algorithmus in Tabellenform
    // Belegart und Betrag (Teil 1)
    bl = "01";            // Belegart Einzahlung in CHF, 03=Nachnahme in CHF, 11=Gutschr. eigenes Konto CHF, 21=Einzahlung in Euro, 23= Gutschr. eigenes Konto Euro
    bg = frm.doc.grand_total * 100;    // Betrag in Rappen aus dem Form.
    if ((bg < 1) || (bg > 9999999999)) {                // 12 Stellen max.
        BBT = "Fehlerhafter Betrag";
    }
    else {
        bt = "000000000000000" + Math.round(bg);
        bt = bt.substr(bt.length -10);        // Auf 10 Stellen auffuellen
        bb = bl + bt;                // Belegart und Betrag aneinanderfuegen
        be = bb.split("");            // und davon einen Array erstellen
        bl = bb.length;                // Anzahl Ziffern in Belegart und Betrag        
        R1 = 0;
        for ( i = 0; i < bl; i++ ) {        // Modulo 10
            Rbb = parseInt(R1) + parseInt(be[i])    // Rest plus entspr. Ziffer - Ganzzahlen
            R1 = alg[Rbb % 10]            // Modulo10 Algorithmus abarbeiten
        }
        P1 = (10 - R1) % 10;    // Pruefziffer (Betrag)
        
        BBT = bb + P1;        // ESR-Code-Zeile - Beleg, Betrag und Pruefziffer
    }
    // Referenznummer (Teil 2)
    referenz = frm.doc.name;
    referenzteil = referenz.split('-')[1];      // Use the main number block from SINV-00001(-1)
    rg = referenzteil;    // Referenznummer ohne Pruefziffer
    rg = "00000000000000000000000000" + rg;
    rg = rg.substr(rg.length - 26);
    rl = rg.length;            // neue Anzahl Ziffern
    ro = rg.split("");            // Array (bereiniget) fuer das Zuordnen in der Tabelle erstellen
    R2 = 0;
    for ( j = 0; j < rl; j++ ) {            // Schleife entsprechend der Anzahl Ziffern
        Rpr = parseInt(R2) + parseInt(ro[j]);    // Rest plus entspr. Ziffer - Ganzzahlen
        R2 = alg[Rpr % 10];            // Modulo10 Algorithmus abarbeiten
    }
    P2 = (10 - R2) % 10;    // Pruefziffer (Referenznummer)

    // RNK Referenznummer, oberhalb der Adresse
    if (rl == 26) {     // entweder 26 Stellen erforderlich
        RNK = ro[0] + ro[1] + " " + ro[2] + ro[3] + ro[4] + ro[5] + ro[6] + " " + ro[7] + ro[8] + ro[9] + ro[10] + ro[11] + " " + ro[12] + ro[13] + ro[14] + ro[15] + ro[16] + " " + ro[17] + ro[18] + ro[19] + ro[20] + ro[21] + " " + ro[22] + ro[23] + ro[24] + ro[25] + P2;
    }
    else if (rl == 15) {     // oder 15 Stellen
        RNK = ro[0] + " " + ro[1]+ ro[2] + ro[3] + ro[4] + ro[5] + " " + ro[6] + ro[7] + ro[8] + ro[9] + ro[10] + " " + ro[11] + ro[12] + ro[13] + ro[14] + P2;    
    }
    RNE = rg + P2;            // Referenznummer in der ESR-Code-Zeile
    // Teilnehmernummer (Teil 3)
    tn = participant_number;    // Teilnehmernummer mit Bindestrichen
    to = tn.split("-");        // ohne Striche
    TN = to.join("");

    // Schreiben der Werte ins Dokument
    frm.doc.esr_reference = RNK;
    frm.doc.esr_code = BBT + ">" + RNE + "+ " + TN + ">";
}  

// this function computes a 27-digit ESR reference (input is a 26-digit code)
function get_esr_code(esr_base) {
    alg = new Array (0,9,4,6,8,2,7,1,3,5);    // vorgebener Algorithmus in Tabellenform
    rg = esr_base.replace(/ /g, '');;
    rl = rg.length;            // neue Anzahl Ziffern
    ro = rg.split("");            // Array (bereiniget) fuer das Zuordnen in der Tabelle erstellen
    R2 = 0;
    for ( j = 0; j < rl; j++ ) {            // Schleife entsprechend der Anzahl Ziffern
        Rpr = parseInt(R2) + parseInt(ro[j]);    // Rest plus entspr. Ziffer - Ganzzahlen
        R2 = alg[Rpr % 10];            // Modulo10 Algorithmus abarbeiten
    }
    P2 = (10 - R2) % 10;    // Pruefziffer (Referenznummer)

    // RNK Referenznummer, oberhalb der Adresse
    if (rl == 26) {     // entweder 26 Stellen erforderlich
        RNK = ro[0] + ro[1] + " " + ro[2] + ro[3] + ro[4] + ro[5] + ro[6] + " " + ro[7] + ro[8] + ro[9] + ro[10] + ro[11] + " " + ro[12] + ro[13] + ro[14] + ro[15] + ro[16] + " " + ro[17] + ro[18] + ro[19] + ro[20] + ro[21] + " " + ro[22] + ro[23] + ro[24] + ro[25] + P2;
    }
    else if (rl == 15) {     // oder 15 Stellen
        RNK = ro[0] + " " + ro[1]+ ro[2] + ro[3] + ro[4] + ro[5] + " " + ro[6] + ro[7] + ro[8] + ro[9] + ro[10] + " " + ro[11] + ro[12] + ro[13] + ro[14] + P2;    
    }
    RNE = rg + P2;            // Referenznummer in der ESR-Code-Zeile
    return RNE;
}  

// this function resolves a pin code and fills the city into the target field of a form
function get_city_from_pincode(pincode, target_field, state_field="", country=null) {
    var filters = [['pincode','=', pincode]];
    if (country) {
        filters.push(['country', '=', country]);
    }
    // find cities
    if (pincode) {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Pincode',
                filters: filters,
                fields: ['name', 'pincode', 'city', 'canton_code']
            },
            async: false,
            callback: function(response) {
                if ((response.message) && (response.message.length > 0)) {
                    if (response.message.length == 1) {
                        // got exactly one city
                        var city = response.message[0].city;
                        cur_frm.set_value(target_field, city);
                        if (state_field != "") {
                            cur_frm.set_value(state_field, response.message[0].canton_code);
                        }
                    } else {
                        // multiple cities found, show selection
                        var cities = "";
                        response.message.forEach(function (record) {
                            cities += (record.city + "\n");
                        });
                        cities = cities.substring(0, cities.length - 1);
                        frappe.prompt([
                                {'fieldname': 'city', 
                                 'fieldtype': 'Select', 
                                 'label': 'City', 
                                 'reqd': 1,
                                 'options': cities,
                                 'default': response.message[0].city
                                }  
                            ],
                            function(values){
                                var city = values.city;
                                cur_frm.set_value(target_field, city);
                                if (state_field != "") {
                                    cur_frm.set_value(state_field, response.message[0].canton_code);
                                }
                            },
                            __('City'),
                            __('Set')
                        );
                    }
                } else {
                    // got no match
                    cur_frm.set_value(target_field, "");
                    console.log("No match");
                }
            }
        });
    }
}

// this function provides a hotfix for min_qty on item prices
function fetch_price_list_rate(frm, cdt, cdn) {
    var item = frappe.get_doc(cdt, cdn);
    var update_stock = 0, show_batch_dialog = 0;
    if(['Sales Invoice'].includes(frm.doc.doctype)) {
        update_stock = cint(frm.doc.update_stock);
        show_batch_dialog = update_stock;

    } else if((frm.doc.doctype === 'Purchase Receipt' && frm.doc.is_return) ||
        frm.doc.doctype === 'Delivery Note') {
        show_batch_dialog = 1;
    }
    // clear barcode if setting item (else barcode will take priority)
    if(!frm.from_barcode) {
        item.barcode = null;
    }
    frappe.call({
        'method': "erpnext.stock.get_item_details.get_item_details",
        'child': item,
        'args': {
            'doc': frm.doc,
            'args': {
                'item_code': item.item_code,
                'barcode': item.barcode,
                'serial_no': item.serial_no,
                'set_warehouse': frm.doc.set_warehouse,
                'warehouse': item.warehouse,
                'customer': frm.doc.customer || frm.doc.party_name,
                'quotation_to': frm.doc.quotation_to,
                'supplier': frm.doc.supplier,
                'currency': frm.doc.currency,
                'update_stock': update_stock,
                'conversion_rate': frm.doc.conversion_rate,
                'price_list': frm.doc.selling_price_list || frm.doc.buying_price_list,
                'price_list_currency': frm.doc.price_list_currency,
                'plc_conversion_rate': frm.doc.plc_conversion_rate,
                'company': frm.doc.company,
                'order_type': frm.doc.order_type,
                'is_pos': cint(frm.doc.is_pos),
                'is_subcontracted': frm.doc.is_subcontracted,
                'transaction_date': frm.doc.transaction_date || frm.doc.posting_date,
                'ignore_pricing_rule': frm.doc.ignore_pricing_rule,
                'doctype': frm.doc.doctype,
                'name': frm.doc.name,
                'project': item.project || frm.doc.project,
                'qty': item.qty || 1,
                'stock_qty': item.stock_qty,
                'conversion_factor': item.conversion_factor,
                'weight_per_unit': item.weight_per_unit,
                'weight_uom': item.weight_uom,
                'uom': item.uom,
                'manufacturer': item.manufacturer,
                'stock_uom': item.stock_uom,
                'pos_profile': frm.doc.doctype == 'Sales Invoice' ? frm.doc.pos_profile : '',
                'cost_center': item.cost_center,
                'tax_category': frm.doc.tax_category,
                'item_tax_template': item.item_tax_template,
                'child_docname': item.name,
            }
        },
        'callback': function(r) {
            if(!r.exc) {
                frappe.model.set_value(cdt, cdn, "price_list_rate", r.message.price_list_rate);
            }
        }
    });
}

function url_to_form(doctype, docname, callback) {
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.common_functions.url_to_form',
        'args': {
            'doctype': doctype,
            'docname': docname
        },              // note: async: false is still not working, response would be undefined
        'callback': callback
    });
}

function link_to_form(doctype, docname, callback) {
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.common_functions.link_to_form',
        'args': {
            'doctype': doctype,
            'docname': docname
        },              // note: async: false is still not working, response would be undefined
        'callback': callback
    });
}

function url_to_list(doctype, callback) {
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.common_functions.url_to_list',
        'args': {
            'doctype': doctype
        },              // note: async: false is still not working, response would be undefined
        'callback': callback
    });
}

function url_to_report(name, callback) {
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.common_functions.url_to_report',
        'args': {
            'name': name
        },              // note: async: false is still not working, response would be undefined
        'callback': callback
    });
}

function url_to_report_with_filters(name, filters, report_type, doctype, callback) {
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.common_functions.url_to_report_with_filters',
        'args': {
            'name': name,
            'filters': filters,
            'report_type': report_type,
            'doctype': doctype
        },              // note: async: false is still not working, response would be undefined
        'callback': callback
    });
}

// get calendar week according to ISO 8601
function get_week(date) {
    if (!(date instanceof Date)) {
        date = new Date(date);
    }

    // ISO week date weeks start on Monday, so correct the day number
    var nDay = (date.getDay() + 6) % 7;

    // ISO 8601 states that week 1 is the week with the first Thursday of that year
    // Set the target date to the Thursday in the target week
    date.setDate(date.getDate() - nDay + 3);

    // Store the millisecond value of the target date
    var n1stThursday = date.valueOf();

    // Set the target to the first Thursday of the year
    // First, set the target to January 1st
    date.setMonth(0, 1);

    // Not a Thursday? Correct the date to the next Thursday
    if (date.getDay() !== 4) {
        date.setMonth(0, 1 + ((4 - date.getDay()) + 7) % 7);
    }

    // The week number is the number of weeks between the first Thursday of the year
    // and the Thursday in the target week (604800000 = 7 * 24 * 3600 * 1000)
    return 1 + Math.ceil((n1stThursday - date) / 604800000);
}

// this will allow to remove the links on an asset, so that the documents can be cancelled
function unlink_asset(force=false) {
    if ((cur_frm.doc.doctype === "Asset") 
        && (!cur_frm.doc.__islocal) 
        &&((cur_frm.doc.docstatus === 0) || (force))) {
        frappe.confirm(
            __('Are you sure you want to unlink {0}?').replace("{0}", cur_frm.doc.name),
            function(){
                // on yes
                frappe.call({
                    'method': 'erpnextswiss.scripts.asset_tools.unlink_asset',
                    'args': {
                        'asset_name': cur_frm.doc.name
                    },
                    'callback': function(response) {
                        cur_frm.reload_doc();
                    }
                });
            },
            function(){
                // on no
            }
        )
    } else {
        frappe.mgsprint( __("Cannot unlink this document") );
    }
}