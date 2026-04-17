let bundle_paste_active = false;
let bundle_timer = null;
let bundle_request_id = 0;

/* =====================================================
   Main Form
===================================================== */

frappe.ui.form.on("Stock Entry", {
	refresh(frm) {
		restrict_actions_for_amazon_invoice(frm);
		set_filters(frm);
		install_bundle_paste_override(frm);
	}
});

frappe.ui.form.on("Stock Entry Detail", {
	item_code(frm, cdt, cdn) {
		let row = get_row(cdt, cdn);
		if (!row) return;

		fetch_item_details(frm, cdt, cdn);

		if (row.parentfield === "bundle_items") {
			trigger_bundle_update(frm, "item_code");
		}
	},

	qty(frm, cdt, cdn) {
		let row = get_row(cdt, cdn);
		if (!row) return;

		if (row.parentfield === "bundle_items") {
			trigger_bundle_update(frm, "qty");
		}
	},

	basic_rate(frm, cdt, cdn) {
		let row = get_row(cdt, cdn);
		if (!row) return;

		if (row.parentfield === "bundle_items") {
			trigger_bundle_update(frm, "basic_rate");
		}
	},

	expense_account(frm, cdt, cdn) {
		let row = get_row(cdt, cdn);
		if (!row) return;

		if (row.parentfield === "bundle_items") {
			trigger_bundle_update(frm, "expense_account");
		}
	},

	bundle_items_add(frm) {
		if (!bundle_paste_active) {
			trigger_bundle_update(frm, "row_add");
		}
	},

	bundle_items_remove(frm) {
		trigger_bundle_update(frm, "row_remove");
	}
});


/* =====================================================
   Helpers
===================================================== */

function get_row(cdt, cdn) {
	return locals[cdt] && locals[cdt][cdn];
}


/* =====================================================
   Paste Override (bundle_items only)
===================================================== */

function install_bundle_paste_override(frm) {
	const wrapper = frm.fields_dict.bundle_items?.wrapper;
	if (!wrapper) return;

	if (wrapper.__bundle_override_installed) return;
	wrapper.__bundle_override_installed = true;

	wrapper.addEventListener(
		"paste",
		async function (e) {
			const target = e.target;

			if (!target.closest(".grid-body")) return;

			e.preventDefault();
			e.stopImmediatePropagation();

			const text = e.clipboardData?.getData("text/plain");
			if (!text) return;

			await process_bundle_paste(frm, text);
		},
		true
	);
}


/* =====================================================
   Custom Bundle Paste
===================================================== */

async function process_bundle_paste(frm, text) {
	bundle_paste_active = true;

	try {
		const rows = parse_tsv(text);
		if (!rows.length) return;

		let start_index = get_target_row_index();

		for (let i = 0; i < rows.length; i++) {
			let row = ensure_bundle_row(frm, start_index + i);
			await set_bundle_row_values(row, rows[i]);
		}

		frm.refresh_field("bundle_items");
	}
	catch (err) {
		console.error(err);
	}
	finally {
		bundle_paste_active = false;
		trigger_bundle_update(frm, "paste_complete");
	}
}

function parse_tsv(text) {
	return text
		.trim()
		.split(/\r?\n/)
		.map(line => line.split("\t"))
		.filter(row => row.some(v => (v || "").trim() !== ""));
}

function get_target_row_index() {
	const active_row = document.activeElement?.closest(".grid-row");
	if (!active_row) return 1;

	return parseInt(active_row.getAttribute("data-idx"), 10) || 1;
}

function ensure_bundle_row(frm, idx) {
	while ((frm.doc.bundle_items || []).length < idx) {
		frm.fields_dict.bundle_items.grid.add_new_row();
	}

	return frm.doc.bundle_items[idx - 1];
}

async function set_bundle_row_values(row, values) {
	const fields = ["item_code", "qty", "basic_rate", "expense_account"];

	for (let i = 0; i < fields.length; i++) {
		if (values[i] == null || values[i] === "") continue;

		let value = values[i];

		if (fields[i] === "qty" || fields[i] === "basic_rate") {
			value = flt(value);
		}

		await frappe.model.set_value(
			row.doctype,
			row.name,
			fields[i],
			value
		);
	}
}


/* =====================================================
   Bundle Rebuild -> items table
===================================================== */

function trigger_bundle_update(frm, source) {
	if (bundle_paste_active) return;

	clearTimeout(bundle_timer);

	bundle_timer = setTimeout(() => {
		run_bundle_update(frm, source);
	}, 300);
}

function run_bundle_update(frm, source) {
	let rows = (frm.doc.bundle_items || []).filter(row =>
		row.item_code && flt(row.qty) > 0
	);

	bundle_request_id++;
	let current = bundle_request_id;

	frappe.call({
		method: "eseller_suite.eseller_suite.custom_script.stock_entry.stock_entry.process_bundle_items",
		args: {
			bundle_items: JSON.stringify(rows)
		},
		callback(r) {
			if (current !== bundle_request_id) return;

			let generated = r.message || [];

			frm.clear_table("items");

			generated.forEach(d => {
				frm.add_child("items", d);
			});

			frm.refresh_field("items");
		}
	});
}


/* =====================================================
   Existing Logic
===================================================== */

function restrict_actions_for_amazon_invoice(frm) {
	if (frm.doc.amazon_invoice_id) {
		frm.disable_form();
		frm.disable_save();
		frm.clear_custom_buttons();
	}
}

function set_filters(frm) {
	frm.set_query("item_code", "bundle_items", () => ({
		filters: { is_bundle_item: 1 }
	}));

	["expense_account", "s_warehouse", "t_warehouse"].forEach(field => {
		frm.set_query(field, "bundle_items", () => ({
			filters: { company: frm.doc.company }
		}));
	});
}

function fetch_item_details(frm, cdt, cdn) {
	let row = get_row(cdt, cdn);
	if (!row || !row.item_code) return;

	frappe.call({
		method: "frappe.client.get",
		args: {
			doctype: "Item",
			name: row.item_code
		},
		callback(r) {
			if (!r.message) return;

			frappe.model.set_value(cdt, cdn, "item_name", r.message.item_name);
			frappe.model.set_value(cdt, cdn, "description", r.message.description);
			frappe.model.set_value(cdt, cdn, "uom", r.message.stock_uom);
		}
	});
}
