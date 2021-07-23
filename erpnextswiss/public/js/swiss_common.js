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
    alg = new Array (0,9,4,6,8,2,7,1,3,5);	// vorgebener Algorithmus in Tabellenform
    // Belegart und Betrag (Teil 1)
    bl = "01";			// Belegart Einzahlung in CHF, 03=Nachnahme in CHF, 11=Gutschr. eigenes Konto CHF, 21=Einzahlung in Euro, 23= Gutschr. eigenes Konto Euro
    bg = frm.doc.grand_total * 100;	// Betrag in Rappen aus dem Form.
    if ((bg < 1) || (bg > 9999999999)) {				// 12 Stellen max.
        BBT = "Fehlerhafter Betrag";
    }
    else {
        bt = "000000000000000" + Math.round(bg);
        bt = bt.substr(bt.length -10);		// Auf 10 Stellen auffuellen
        bb = bl + bt;				// Belegart und Betrag aneinanderfuegen
        be = bb.split("");			// und davon einen Array erstellen
        bl = bb.length;				// Anzahl Ziffern in Belegart und Betrag		
        R1 = 0;
        for ( i = 0; i < bl; i++ ) {		// Modulo 10
            Rbb = parseInt(R1) + parseInt(be[i])	// Rest plus entspr. Ziffer - Ganzzahlen
            R1 = alg[Rbb % 10]			// Modulo10 Algorithmus abarbeiten
        }
        P1 = (10 - R1) % 10;	// Pruefziffer (Betrag)
        
        BBT = bb + P1;		// ESR-Code-Zeile - Beleg, Betrag und Pruefziffer
    }
    // Referneznummer (Teil 2)
    referenz = frm.doc.name;
    referenzteil = referenz.split('-')[1];      // Use the main number block from SINV-00001(-1)
    rg = referenzteil;	// Referenznummer ohne Pruefziffer
    rg = "00000000000000000000000000" + rg;
    rg = rg.substr(rg.length - 26);
    rl = rg.length;			// neue Anzahl Ziffern
    ro = rg.split("");			// Array (bereiniget) fuer das Zuordnen in der Tabelle erstellen
    R2 = 0;
    for ( j = 0; j < rl; j++ ) {			// Schleife entsprechend der Anzahl Ziffern
        Rpr = parseInt(R2) + parseInt(ro[j]);	// Rest plus entspr. Ziffer - Ganzzahlen
        R2 = alg[Rpr % 10];			// Modulo10 Algorithmus abarbeiten
    }
    P2 = (10 - R2) % 10;	// Pruefziffer (Referenznummer)

    // RNK Referenznummer, oberhalb der Adresse
    if (rl == 26) { 	// entweder 26 Stellen erforderlich
        RNK = ro[0] + ro[1] + " " + ro[2] + ro[3] + ro[4] + ro[5] + ro[6] + " " + ro[7] + ro[8] + ro[9] + ro[10] + ro[11] + " " + ro[12] + ro[13] + ro[14] + ro[15] + ro[16] + " " + ro[17] + ro[18] + ro[19] + ro[20] + ro[21] + " " + ro[22] + ro[23] + ro[24] + ro[25] + P2;
    }
    else if (rl == 15) { 	// oder 15 Stellen
        RNK = ro[0] + " " + ro[1]+ ro[2] + ro[3] + ro[4] + ro[5] + " " + ro[6] + ro[7] + ro[8] + ro[9] + ro[10] + " " + ro[11] + ro[12] + ro[13] + ro[14] + P2;	
    }
    RNE = rg + P2;			// Referenznummer in der ESR-Code-Zeile
    // Teilnehmernummer (Teil 3)
    tn = participant_number;	// Teilnehmernummer mit Bindestrichen
    to = tn.split("-");		// ohne Striche
    TN = to.join("");

    // Schreiben der Werte ins Dokument
    frm.doc.esr_reference = RNK;
    frm.doc.esr_code = BBT + ">" + RNE + "+ " + TN + ">";
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
                if (response.message) {
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
