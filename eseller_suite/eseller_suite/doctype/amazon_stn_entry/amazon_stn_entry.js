// Copyright (c) 2026, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("Amazon STN Entry", {
	refresh(frm) {
		if (!frm.is_new()) {
			set_error_messages_html(frm);
		}
		hanlde_retry_btn(frm);
	},
	stn_file(frm) {
		if (!frm.doc.stn_file) {
			frm.clear_table("stn_entries");
			frm.refresh_field("stn_entries");
		}
	}
});

function set_error_messages_html(frm) {
	frm.call('get_error_message_html').then(r => {
		if (r.message) {
			frm.set_df_property('section_break_ijoc', 'hidden', 0);
			var data = r.message;
			$(frm.fields_dict['error_messages_html'].wrapper).html(data);
			frm.refresh_fields();
		}
		else {
			frm.set_df_property('section_break_ijoc', 'hidden', 1);
			$(frm.fields_dict['error_messages_html'].wrapper).html('');
			frm.refresh_fields();
		}
	});
}

function hanlde_retry_btn(frm) {
	if (frm.doc.docstatus === 0 && !frm.is_new()) {
		frm.add_custom_button('Re-try', () => {
			frm.call('retry_fetching_data').then(r => {
				if (r.message) {
					frm.reload_doc();
				}
			})
		})
	}
}