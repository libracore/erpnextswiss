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

// this function resolves a pin code and fills the city into the target field of a form
function get_city_from_pincode(pincode, target_field) {
    // find cities
    if (pincode) {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Pincode',
                filters: [
                    ['pincode','=', pincode]
                ],
                fields: ['name', 'pincode', 'city']
            },
            async: false,
            callback: function(response) {
                if (response.message) {
                    if (response.message.length == 1) {
                        // got exactly one city
                        var city = response.message[0].city;
                        cur_frm.set_value(target_field, city);
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
                            },
                            __('City'),
                            __('Set')
                        );
                    }
                } else {
                    // got no match
                    cur_frm.set_value(target_field, "");
                }
            }
        });
    }
}
