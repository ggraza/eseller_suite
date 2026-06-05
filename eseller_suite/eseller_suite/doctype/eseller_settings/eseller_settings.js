// Copyright (c) 2024, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("eSeller Settings", {
    refresh(frm) {
        set_filters(frm);
        set_sales_invoice_series(frm);
        set_custom_buttons(frm);
    },
    allow_missing_warehouse_creation(frm) {
        if (frm.doc.allow_missing_warehouse_creation) {
            populate_parent_warehouses(frm);
        } else {
            clear_parent_warehouses(frm);
        }
    }
});

frappe.ui.form.on("Amazon Payment Account", {
    payment_accounts_add(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, 'company', '');
        frappe.model.set_value(cdt, cdn, 'mode_of_payment', frm.doc.default_mode_of_payment);
        frappe.model.set_value(cdt, cdn, 'use_reserve_lines_in_amazon_payment_entry', frm.doc.use_reserve_lines_in_amazon_payment_entry);
    },
});

frappe.ui.form.on("eSeller Parent Warehouse", {
    parent_warehouses_add(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, 'company', '');
    },
});

function set_filters(frm) {
    frm.set_query("main_warehouse", () => {
        return {
            filters: {
                "is_group": 0
            }
        };
    });
    frm.set_query("inter_company_price_list", () => {
        return {
            filters: {
                "buying": 1,
                "selling": 1,
            }
        };
    });
    frm.set_query('default_parent_warehouse', 'parent_warehouses', (doc, cdt, cdn) => {
        let row = locals[cdt][cdn];
        return {
            filters: {
                company: row.company || "",
                is_group: 1
            }
        };
    });
    default_account_filters(frm);
}

/**
 * Populate parent warehouses via server call Clears parent warehouses when checkbox is unchecked
 */
function populate_parent_warehouses(frm) {
    frappe.call({
        method: "eseller_suite.eseller_suite.doctype.eseller_settings.eseller_settings.get_all_companies",
        callback: function (r) {
            if (r.message) {
                frm.clear_table("parent_warehouses");

                r.message.forEach(comp => {
                    let row = frm.add_child("parent_warehouses");
                    row.company = comp.name;
                });

                frm.refresh_field("parent_warehouses");
            }
        }
    });
}

/*
 * Clear table when checkbox unchecked
 */
function clear_parent_warehouses(frm) {
    frm.clear_table("parent_warehouses");
    frm.refresh_field("parent_warehouses");
}

function default_account_filters(frm) {
    frm.set_query('inventory_reimbursement_income_account', 'payment_accounts', (doc, cdt, cdn) => {
        let row = locals[cdt][cdn];
        return {
            filters: {
                company: row.company || "",
                is_group: 0
            }
        };
    });
    frm.set_query('other_income_account', 'payment_accounts', (doc, cdt, cdn) => {
        let row = locals[cdt][cdn];
        return {
            filters: {
                company: row.company || "",
                is_group: 0
            }
        };
    });
    frm.set_query('amazon_reserve_fund_account', 'payment_accounts', (doc, cdt, cdn) => {
        let row = locals[cdt][cdn];
        return {
            filters: {
                company: row.company || "",
                is_group: 0
            }
        };
    });
    frm.set_query('inventory_reimbursement_account', 'payment_accounts', (doc, cdt, cdn) => {
        let row = locals[cdt][cdn];
        return {
            filters: {
                company: row.company || "",
                is_group: 0
            }
        };
    });
    frm.set_query('other_expenses_account', 'payment_accounts', (doc, cdt, cdn) => {
        let row = locals[cdt][cdn];
        return {
            filters: {
                company: row.company || "",
                is_group: 0
            }
        };
    });
    frm.set_query('order_cancellation_account', 'payment_accounts', (doc, cdt, cdn) => {
        let row = locals[cdt][cdn];
        return {
            filters: {
                company: row.company || "",
                is_group: 0
            }
        };
    });
    frm.set_query('amazon_reserve_income_account', 'payment_accounts', (doc, cdt, cdn) => {
        let row = locals[cdt][cdn];
        return {
            filters: {
                company: row.company || "",
                is_group: 0
            }
        };
    });
    frm.set_query('amazon_reserve_expense_account', 'payment_accounts', (doc, cdt, cdn) => {
        let row = locals[cdt][cdn];
        return {
            filters: {
                company: row.company || "",
                is_group: 0
            }
        };
    });
}

function set_sales_invoice_series(frm) {
    frappe.call('eseller_suite.eseller_suite.doctype.eseller_settings.eseller_settings.get_naming_series_options').then(r => {
        frm.set_df_property('stn_sales_invoice_series', 'options', r.message.join("\n"));
    })
}

function set_custom_buttons(frm) {
    if (frappe.session.user === "Administrator") {
        frm.add_custom_button('Update SI Items', () => {
            frappe.call('eseller_suite.eseller_suite.utils.update_missing_items_in_sales_invoices').then(r => {
                frappe.msgprint('Successfull');
            })
        }, __("Patches"));

        frm.add_custom_button('Delete Invoices with negative stock', () => {
            frappe.call('eseller_suite.eseller_suite.utils.delete_submitted_invoices_without_stock').then(r => {
                frappe.msgprint('Successfull');
            })
        }, __("Patches"));

        frm.add_custom_button('Delete Invoices without GLE', () => {
            frappe.call('eseller_suite.eseller_suite.utils.delete_submitted_invoices_without_gle').then(r => {
                frappe.msgprint('Successfull');
            })
        }, __("Patches"));

        frm.add_custom_button('Delete SO without SI', () => {
            frappe.call('eseller_suite.eseller_suite.utils.delete_submitted_so_without_si').then(r => {
                frappe.msgprint('Successfull');
            })
        }, __("Patches"));
    }
}