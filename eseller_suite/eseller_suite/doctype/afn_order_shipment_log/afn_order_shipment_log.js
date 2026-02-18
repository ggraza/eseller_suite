// Copyright (c) 2026, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("AFN Order Shipment Log", {
    refresh(frm) {
        frm.disable_save();
        frm.disable_form();
    },
});
