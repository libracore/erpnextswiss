// Copyright (c) 2019, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Calibration Test', {
	refresh: function(frm) {

	},
	perform_test: function (frm) {
		var div_for_test = document.getElementById("perform_test_div");
		div_for_test.appendChild(create_div_list(frm));
		var items = cur_frm.doc.test_plan_items;
		var to_open = '';
		items.forEach(function(entry) {
			div_for_test.appendChild(create_div_tests(frm, entry));
			if (entry.inspection_decision_ok == '0') {
				if (to_open == '') {
					to_open = entry.name;
				}
			}
		});
		console.log(to_open);
		if (to_open != '') {
			document.getElementById(to_open + "_to_open").click();
		}
	}
});

function create_div_list(frm) {
	var col_4_container = document.createElement("div");
	col_4_container.classList.add("col-sm-4");
	
	var col_4_container_ol = document.createElement("ol");
	
	var items = cur_frm.doc.test_plan_items;
	items.forEach(function(entry) {
		var li = document.createElement("li");
		var fontawesome = document.createElement("i");
		if (entry.inspection_decision_ok == 1) {
			fontawesome.classList.add("fa");
			fontawesome.classList.add("fa-check");
		} else {
			fontawesome.classList.add("fa");
			fontawesome.classList.add("fa-times");
		}
		li.appendChild(fontawesome);
		var a = document.createElement("a");
		a.innerHTML = " " + entry.designation;
		a.id = entry.name + "_to_open";
		a.onclick = function() { toggle_hidden(entry.name); };
		li.appendChild(a);
		col_4_container_ol.appendChild(li);
	});
	
	col_4_container.appendChild(col_4_container_ol);
	
	return col_4_container
}

function create_div_tests(frm, entry) {
	if (entry.test_based_on == "Verdict") {
		// column container
		var col_8_container = document.createElement("div");
		col_8_container.id = entry.name;
		col_8_container.classList.add("col-sm-8");
		col_8_container.classList.add("single-tests");
		col_8_container.classList.add("hidden");
		
		//title
		var title = document.createElement("h2");
		title.innerHTML = entry.designation;
		title.style.marginTop = "0px";
		col_8_container.appendChild(title);
		
		//Operating Instructions
		var form_group = document.createElement("div");
		form_group.classList.add("form-group");
		var label_operating_instructions = document.createElement("label");
		label_operating_instructions.for = entry.name + "_" + "operating_instructions";
		label_operating_instructions.innerHTML = __("Operating Instructions");
		var operating_instructions = document.createElement("textarea");
		operating_instructions.classList.add("form-control");
		operating_instructions.innerHTML = entry.operating_instructions;
		operating_instructions.id = entry.name + "_" + "operating_instructions";
		operating_instructions.disabled = true;
		
		//Remarks
		var label_remarks = document.createElement("label");
		label_remarks.for = entry.name + "_" + "remarks";
		label_remarks.innerHTML = __("Remarks");
		var remarks = document.createElement("textarea");
		remarks.classList.add("form-control");
		remarks.innerHTML = entry.remarks || '';
		remarks.id = entry.name + "_" + "remarks";
		
		//Inspection Decision OK Button
		var button = document.createElement("button");
		button.type = "button";
		button.classList.add("btn");
		button.classList.add("btn-success");
		button.innerHTML = "Inspection Decision OK";
		button.style.marginTop = "5px";
		button.onclick = function() { save_values(frm, entry.name, entry.test_based_on, document.getElementById(entry.name + "_" + "remarks").value); };
		
		//combine everything
		form_group.appendChild(label_operating_instructions);
		form_group.appendChild(operating_instructions);
		form_group.appendChild(label_remarks);
		form_group.appendChild(remarks);
		form_group.appendChild(button);
		
		col_8_container.appendChild(form_group);
		
		return col_8_container
	}
	
	if (entry.test_based_on == "Value") {
		// column container
		var col_8_container = document.createElement("div");
		col_8_container.id = entry.name;
		col_8_container.classList.add("col-sm-8");
		col_8_container.classList.add("single-tests");
		col_8_container.classList.add("hidden");
		
		//title
		var title = document.createElement("h2");
		title.innerHTML = entry.designation;
		title.style.marginTop = "0px";
		col_8_container.appendChild(title);
		
		//Operating Instructions
		var form_group = document.createElement("div");
		form_group.classList.add("form-group");
		var label_operating_instructions = document.createElement("label");
		label_operating_instructions.for = entry.name + "_" + "operating_instructions";
		label_operating_instructions.innerHTML = __("Operating Instructions");
		var operating_instructions = document.createElement("textarea");
		operating_instructions.classList.add("form-control");
		operating_instructions.innerHTML = entry.operating_instructions;
		operating_instructions.id = entry.name + "_" + "operating_instructions";
		operating_instructions.disabled = true;
		
		//Remarks
		var label_remarks = document.createElement("label");
		label_remarks.for = entry.name + "_" + "remarks";
		label_remarks.innerHTML = __("Remarks");
		var remarks = document.createElement("textarea");
		remarks.classList.add("form-control");
		remarks.innerHTML = entry.remarks || '';
		remarks.id = entry.name + "_" + "remarks";
		
		//table
		var table = document.createElement("table");
		table.style.width = "100%";
		table.style.marginTop = "5px";
		
		//table header
		var tr1 = document.createElement("tr");
		var th1 = document.createElement("th");
		th1.innerHTML = __("Nominal Value");
		var th2 = document.createElement("th");
		th2.innerHTML = __("OTG");
		var th3 = document.createElement("th");
		th3.innerHTML = __("UTG");
		var th4 = document.createElement("th");
		th4.innerHTML = __("Actual Value");
		tr1.appendChild(th1);
		tr1.appendChild(th2);
		tr1.appendChild(th3);
		tr1.appendChild(th4);
		table.appendChild(tr1);
		
		//table body
		var tr2 = document.createElement("tr");
		var td1 = document.createElement("td");
		td1.innerHTML = entry.nominal_value;
		var td2 = document.createElement("td");
		td2.innerHTML = entry.otg;
		var td3 = document.createElement("td");
		td3.innerHTML = entry.utg;
		var td4 = document.createElement("td");
		var td4_input = document.createElement("input");
		td4_input.type = "text";
		td4_input.classList.add("form-control");
		td4_input.id = entry.name + "_" + "actual_value";
		td4_input.value = entry.actual_value || '';
		td4.appendChild(td4_input);
		tr2.appendChild(td1);
		tr2.appendChild(td2);
		tr2.appendChild(td3);
		tr2.appendChild(td4);
		table.appendChild(tr2);
		
		//Inspection Decision OK Button
		var button = document.createElement("button");
		button.type = "button";
		button.classList.add("btn");
		button.classList.add("btn-success");
		button.innerHTML = "Inspection Decision OK";
		button.style.marginTop = "5px";
		button.onclick = function() { save_values(frm, entry.name, entry.test_based_on, document.getElementById(entry.name + "_" + "remarks").value); };
		
		//combine everything
		form_group.appendChild(label_operating_instructions);
		form_group.appendChild(operating_instructions);
		form_group.appendChild(table);
		form_group.appendChild(label_remarks);
		form_group.appendChild(remarks);
		form_group.appendChild(button);
		
		col_8_container.appendChild(form_group);
		
		return col_8_container
	}
}

function toggle_hidden(name) {
	var all_divs = document.getElementsByClassName("single-tests");
	var i;
	for (i=0;i<all_divs.length;i++) {
		all_divs[i].classList.add("hidden");
	}
	var to_toggle = document.getElementById(name);
	to_toggle.classList.toggle("hidden");
}

function save_values(frm, name, type, remarks) {
	//frappe.msgprint("jetzt sollte es gespeichert werden...typ: " + type + ", name: " + name);
	var all_tests = cur_frm.doc.test_plan_items;
	var i;
	for (i=0; i < all_tests.length; i++) {
		if (all_tests[i].name == name) {
			frappe.model.set_value(cur_frm.doc.test_plan_items[i].doctype, cur_frm.doc.test_plan_items[i].name, "remarks", remarks);
			frappe.model.set_value(cur_frm.doc.test_plan_items[i].doctype, cur_frm.doc.test_plan_items[i].name, "inspection_decision_ok", 1);
		}
	}
	cur_frm.save();
	setTimeout(function(){ cur_frm.events.perform_test(); }, 1000);
	
}