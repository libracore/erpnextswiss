frappe.listview_settings['Inspection Equipment'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if(doc.status == 'Calibrated') {
			return [__("Calibrated"), "green", "status,=,Calibrated"];
		} else if(doc.status == 'To Calibrate') {
			return [__("To Calibrate"), "orange", "status,=,To Calibrate"]
		} else if(doc.status == 'Without Calibration') {
			return [__("Without Calibration"), "green", "status,=,Without Calibration"]
		} else if(doc.status == 'Disabled') {
			return [__("Disabled"), "darkgrey", "status,=,Disabled"]
		} else if(doc.status == 'Scrap') {
			return [__("Scrap"), "darkgrey", "status,=,Scrap"]
		}
	}
};