// Copyright (c) 2019, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Non Conformity Report 8D', {
	refresh: function(frm) {
		if (frm.doc.status == "Completed") {
			cur_frm.set_df_property("title","read_only",1);
			cur_frm.set_df_property("interim_containment_plan","read_only",1);
			cur_frm.set_df_property("customer","read_only",1);
			cur_frm.set_df_property("d1_team","read_only",1);
			cur_frm.set_df_property("d1_complete","read_only",1);
			cur_frm.set_df_property("problem_description","read_only",1);
			cur_frm.set_df_property("d2_complete","read_only",1);
			cur_frm.set_df_property("d3_complete","read_only",1);
			cur_frm.set_df_property("d4_complete","read_only",1);
			cur_frm.set_df_property("d5_complete","read_only",1);
			cur_frm.set_df_property("d6_complete","read_only",1);
			cur_frm.set_df_property("d7_complete","read_only",1);
			cur_frm.set_df_property("d8_complete","read_only",1);
			cur_frm.set_df_property("root_cause_analysis","read_only",1);
			cur_frm.set_df_property("remedial_actions","read_only",1);
			frm.add_custom_button(__("Reopen 8D"),  function() { reopen(frm); });
		}
	}
});

function reopen(frm) {
	cur_frm.set_df_property("title","read_only",0);
	cur_frm.set_df_property("interim_containment_plan","read_only",0);
	cur_frm.set_df_property("customer","read_only",0);
	cur_frm.set_df_property("d1_team","read_only",0);
	cur_frm.set_df_property("d1_complete","read_only",0);
	cur_frm.set_df_property("problem_description","read_only",0);
	cur_frm.set_df_property("d2_complete","read_only",0);
	cur_frm.set_df_property("d3_complete","read_only",0);
	cur_frm.set_df_property("d4_complete","read_only",0);
	cur_frm.set_df_property("d5_complete","read_only",0);
	cur_frm.set_df_property("d6_complete","read_only",0);
	cur_frm.set_df_property("d7_complete","read_only",0);
	cur_frm.set_df_property("d8_complete","read_only",0);
	cur_frm.set_df_property("root_cause_analysis","read_only",0);
	cur_frm.set_df_property("remedial_actions","read_only",0);
	cur_frm.set_value('status', 'Reopen');
}