// Copyright (c) 2019, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Calibration Test', {
	refresh: function(frm) {

	},
	perform_test: function (frm) {
		//frappe.msgprint('<div class="col-4"><p>hier folgt die liste...</p></div><div class="col-8"><p>hier die einzelnen punkte...</p></div>');
		var div_for_test = document.getElementById("perform_test_div");
		div_for_test.appendChild(create_div_list(frm));
		var items = cur_frm.doc.test_plan_items;
		items.forEach(function(entry) {
			div_for_test.appendChild(create_div_tests(entry));
		});
	}
});

function create_div_list(frm) {
	var col_4_container = document.createElement("div");
	col_4_container.classList.add("col-sm-4");
	
	var col_4_container_ol = document.createElement("ol");
	
	var items = cur_frm.doc.test_plan_items;
	items.forEach(function(entry) {
		var li = document.createElement("li");
		var a = document.createElement("a");
		a.innerHTML = entry.designation;
		a.onclick = function() { toggle_hidden(entry.name); };
		//a.addEventListener("click", toggle_hidden(entry.name), false);
		li.appendChild(a);
		col_4_container_ol.appendChild(li);
	});
	
	col_4_container.appendChild(col_4_container_ol);
	
	return col_4_container
}

function create_div_tests(entry) {
	var col_8_container = document.createElement("div");
	col_8_container.id = entry.name;
	col_8_container.classList.add("col-sm-8");
	col_8_container.classList.add("hidden");
	
	var p = document.createElement("p");
	p.innerHTML = entry.designation;
	
	
	col_8_container.appendChild(p);
	
	return col_8_container
}

function toggle_hidden(name) {
	var to_toggle = document.getElementById(name);
	to_toggle.classList.toggle("hidden");
}