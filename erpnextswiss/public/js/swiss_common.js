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