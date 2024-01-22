frappe.pages['worldline-tim-test'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Worldline TIM Test',
        single_column: true
    });
    page.main.html(frappe.render_template("worldline_tim_test_html", {}));
}

function onTimApiReady() {
    let script = document.createElement("script");
    script.src = "/assets/erpnextswiss/js/tim/testing/app.js";
    document.getElementsByTagName("head")[0].appendChild(script);
}
