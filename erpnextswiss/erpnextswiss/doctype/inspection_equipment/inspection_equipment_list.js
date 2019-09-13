frappe.listview_settings['Inspection Equipment'] = {
	add_fields: ["status", "transaction_status"],
	get_indicator: function(doc) {
		var colors = {
			"Calibrated/On Stock": "green",
			"Calibrated/Taken": "blue",
			"To Calibrate/On Stock": "red",
			"To Calibrate/Taken": "red",
			"Without Calibration/On Stock": "green",
			"Without Calibration/Taken": "blue",
			"Disabled/On Stock": "darkgrey",
			"Scrap/On Stock": "darkgrey",
			"Disabled/Taken": "darkgrey",
			"Scrap/Taken": "darkgrey"
		};
		var to_display = {
			"Calibrated/On Stock": "Calibrated and on stock",
			"Calibrated/Taken": "Calibrated and taken",
			"To Calibrate/On Stock": "To calibrate and on stock",
			"To Calibrate/Taken": "To calibrate and taken",
			"Without Calibration/On Stock": "Without calibration and on stock",
			"Without Calibration/Taken": "Without calibration and taken",
			"Disabled/On Stock": "Disabled",
			"Scrap/On Stock": "Scrap",
			"Disabled/Taken": "Disabled",
			"Scrap/Taken": "Scrap"
		};
		return [__(to_display[doc.status+"/"+doc.transaction_status]), colors[doc.status+"/"+doc.transaction_status], "status,=," + doc.status+"|transaction_status,=,"+doc.transaction_status];
	}
};