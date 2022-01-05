frappe.listview_settings['Non Conformity Report 8D'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if (doc.status == "Completed") {
		return [__("Completed"), "green", "status,=,Completed"]
		} else if (doc.status == "New") {
			return [__("New"), "red", "status,=,New"]
		} else if (doc.status == "D2") {
			return [__("D2"), "orange", "status,=,D2"]
		} else if (doc.status == "D3") {
			return [__("D3"), "orange", "status,=,D3"]
		} else if (doc.status == "D4") {
			return [__("D4"), "orange", "status,=,D4"]
		} else if (doc.status == "D5") {
			return [__("D5"), "orange", "status,=,D5"]
		} else if (doc.status == "D6") {
			return [__("D6"), "orange", "status,=,D6"]
		} else if (doc.status == "D7") {
			return [__("D7"), "orange", "status,=,D7"]
		} else if (doc.status == "D8") {
			return [__("D8"), "orange", "status,=,D8"]
		}
	}
};