// check if HLK is active, if so, load HLK extension
try {
    frappe.call({
    "method": "erpnextswiss.erpnextswiss.domains.is_domain_active",
    "args": {
        "domain": "HLK"
    },
    "callback": function(response) {
        if (response.message === 1) {
            // load HLK
            var script = document.createElement('script');
            script.onload = function () {
                cur_frm.refresh();
            };
            script.src = "/assets/erpnextswiss/js/hlk_scripts/quotation.js";
            document.head.appendChild(script);
        }
    }
});

} catch {
    // do nothing
}

// normal scripts
frappe.ui.form.on('Quotation', {
    onload(frm) {
        capture_copied_quotation_pricing(frm);
    },
    refresh(frm) {
        capture_copied_quotation_pricing(frm);
        schedule_restore_copied_quotation_pricing(frm);
    },
    party_name(frm) {
        schedule_restore_copied_quotation_pricing(frm);
    },
    quotation_to(frm) {
        schedule_restore_copied_quotation_pricing(frm);
    },
    selling_price_list(frm) {
        schedule_restore_copied_quotation_pricing(frm);
    },
    before_save(frm) {
        if (frm._copied_quotation_pricing_pending_restore) {
            restore_copied_quotation_pricing(frm);
        }
    }
});

const copiedQuotationPricingFields = [
    "price_list_rate",
    "discount_percentage",
    "discount_amount",
    "rate",
    "net_rate",
    "margin_type",
    "margin_rate_or_amount",
    "rate_with_margin",
    "do_not_show_discount"
];

function capture_copied_quotation_pricing(frm) {
    if (!frm || !frm.doc || !frm.is_new || !frm.is_new()) {
        return;
    }
    if (frm._copied_quotation_pricing) {
        return;
    }

    const snapshot = (frm.doc.items || [])
        .filter((row) => row && row.item_code && quotation_row_has_pricing(row))
        .map((row) => {
            const values = {
                row_name: row.name || null,
                idx: cint(row.idx),
                item_code: row.item_code
            };

            copiedQuotationPricingFields.forEach((fieldname) => {
                if (row[fieldname] !== undefined) {
                    values[fieldname] = row[fieldname];
                }
            });

            return values;
        });

    if (snapshot.length) {
        frm._copied_quotation_pricing = snapshot;
    }
}

function quotation_row_has_pricing(row) {
    return copiedQuotationPricingFields.some((fieldname) => quotation_value_is_set(row[fieldname]));
}

function quotation_value_is_set(value) {
    return !(value === undefined || value === null || value === "");
}

function schedule_restore_copied_quotation_pricing(frm) {
    if (!frm || !frm._copied_quotation_pricing || !frm.is_new || !frm.is_new()) {
        return;
    }

    frm._copied_quotation_pricing_pending_restore = true;

    if (frm._copied_quotation_pricing_timers) {
        frm._copied_quotation_pricing_timers.forEach((timer) => clearTimeout(timer));
    }
    if (frm._copied_quotation_pricing_release_timer) {
        clearTimeout(frm._copied_quotation_pricing_release_timer);
    }

    frm._copied_quotation_pricing_timers = [0, 180, 650].map((delay) =>
        setTimeout(() => restore_copied_quotation_pricing(frm), delay)
    );
    frm._copied_quotation_pricing_release_timer = setTimeout(() => {
        frm._copied_quotation_pricing_pending_restore = false;
    }, 1200);
}

function restore_copied_quotation_pricing(frm) {
    if (!frm || !frm.doc || !frm._copied_quotation_pricing || !frm.is_new || !frm.is_new()) {
        return false;
    }

    let changed = false;

    (frm.doc.items || []).forEach((row) => {
        const snapshot = find_copied_quotation_pricing(frm, row);
        if (!snapshot) {
            return;
        }

        copiedQuotationPricingFields.forEach((fieldname) => {
            if (!quotation_value_is_set(snapshot[fieldname])) {
                return;
            }
            if (quotation_field_values_match(row[fieldname], snapshot[fieldname])) {
                return;
            }
            row[fieldname] = snapshot[fieldname];
            changed = true;
        });

        const qty = flt(row.qty);
        const rate = flt(quotation_value_is_set(snapshot.rate) ? snapshot.rate : row.rate);
        const netRate = flt(quotation_value_is_set(snapshot.net_rate) ? snapshot.net_rate : rate);
        const amount = qty * rate;
        const netAmount = qty * netRate;

        if (!quotation_numbers_match(row.amount, amount)) {
            row.amount = amount;
            changed = true;
        }
        if (!quotation_numbers_match(row.net_amount, netAmount)) {
            row.net_amount = netAmount;
            changed = true;
        }
    });

    if (changed) {
        refresh_copied_quotation_pricing(frm);
    }

    return changed;
}

function find_copied_quotation_pricing(frm, row) {
    return (frm._copied_quotation_pricing || []).find((entry) => {
        if (entry.row_name && row.name && entry.row_name === row.name) {
            return true;
        }
        return entry.item_code === row.item_code && cint(entry.idx) === cint(row.idx);
    });
}

function quotation_field_values_match(current, next) {
    if (typeof current === "number" || typeof next === "number") {
        return quotation_numbers_match(current, next);
    }
    return current === next;
}

function quotation_numbers_match(current, next) {
    return Math.abs(flt(current) - flt(next)) <= 0.000001;
}

function refresh_copied_quotation_pricing(frm) {
    if (frm.cscript && typeof frm.cscript.calculate_taxes_and_totals === "function") {
        frm.cscript.calculate_taxes_and_totals();
    } else if (frm.script_manager && typeof frm.script_manager.trigger === "function") {
        frm.script_manager.trigger("calculate_taxes_and_totals");
    }

    frm.refresh_field("items");
    ["total", "net_total", "grand_total", "discount_amount"].forEach((fieldname) => {
        if (frm.fields_dict && frm.fields_dict[fieldname]) {
            frm.refresh_field(fieldname);
        }
    });
}
