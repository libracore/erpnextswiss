// Copyright (c) 2026, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on("Salary Slip", {
    refresh(frm) {
        render_quellensteuer(frm);
    }
});

function render_quellensteuer(frm) {
    const field = frm.get_field("qst_calculation");
    if (!field) return;
    if (frm.is_new() || !(frm.doc.qst_details || []).length) {
        field.$wrapper.empty();
        return;
    }
    frappe.call({
        method: "erpnextswiss.erpnextswiss.quellensteuer.payroll.explain_slip",
        args: {salary_slip: frm.doc.name},
        callback: (response) => {
            const rows = (response.message || []).map((row) => `<tr>
                <td class="text-muted" style="white-space: nowrap">${frappe.utils.escape_html(row.period)}</td>
                <td class="text-muted" style="white-space: nowrap">${frappe.utils.escape_html(row.entry_type)}</td>
                <td>${frappe.utils.escape_html(row.calculation)}</td></tr>`).join("");
            field.$wrapper.html(rows ? `<table class="table table-bordered" style="margin: 0"><tbody>${rows}</tbody></table>` : "");
        }
    });
}
