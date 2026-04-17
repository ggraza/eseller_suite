let bundle_paste_active = false;
let bundle_timer = null;
let bundle_request_id = 0;

/* =====================================================
   Debug Logger
   Filter by "[Bundle]" in DevTools console.
   Set BUNDLE_DEBUG = false to silence in production.
===================================================== */
const BUNDLE_DEBUG = false;

function dbg(...args) {
	if (!BUNDLE_DEBUG) return;
	console.log("[Bundle]", ...args);
}

function dbg_warn(...args) {
	if (!BUNDLE_DEBUG) return;
	console.warn("[Bundle] ⚠", ...args);
}

function dbg_table(label, data) {
	if (!BUNDLE_DEBUG) return;
	console.groupCollapsed("[Bundle] " + label);
	console.table(data);
	console.groupEnd();
}


/* =====================================================
   Main Form
===================================================== */

frappe.ui.form.on("Stock Entry", {
	refresh(frm) {
		dbg("─── refresh ───────────────────────────────────────");
		dbg("docname:", frm.doc.name);
		dbg("from_warehouse:", frm.doc.from_warehouse, "| to_warehouse:", frm.doc.to_warehouse);
		dbg("amazon_invoice_id:", frm.doc.amazon_invoice_id);
		restrict_actions_for_amazon_invoice(frm);
		set_filters(frm);
		install_bundle_paste_override(frm);
	},
	from_warehouse(frm) {
		dbg("from_warehouse changed:", frm.doc.from_warehouse);
		set_warehouses(frm);
		trigger_bundle_update(frm, "from_warehouse change");
	},
	to_warehouse(frm) {
		dbg("to_warehouse changed:", frm.doc.to_warehouse);
		set_warehouses(frm);
		trigger_bundle_update(frm, "to_warehouse change");
	}
});

frappe.ui.form.on("Stock Entry Detail", {
	item_code(frm, cdt, cdn) {
		let row = get_row(cdt, cdn);
		if (!row) return;

		dbg("item_code changed | parentfield:", row.parentfield, "| idx:", row.idx, "| value:", row.item_code);
		fetch_item_details(frm, cdt, cdn);

		if (row.parentfield === "bundle_items") {
			trigger_bundle_update(frm, "item_code");
		}
	},

	qty(frm, cdt, cdn) {
		let row = get_row(cdt, cdn);
		if (!row) return;

		dbg("qty changed | parentfield:", row.parentfield, "| idx:", row.idx, "| item_code:", row.item_code, "| qty:", row.qty);
		if (row.parentfield === "bundle_items") {
			trigger_bundle_update(frm, "qty");
		}
	},

	basic_rate(frm, cdt, cdn) {
		let row = get_row(cdt, cdn);
		if (!row) return;

		dbg("basic_rate changed | parentfield:", row.parentfield, "| idx:", row.idx, "| item_code:", row.item_code, "| basic_rate:", row.basic_rate);
		if (row.parentfield === "bundle_items") {
			trigger_bundle_update(frm, "basic_rate");
		}
	},

	expense_account(frm, cdt, cdn) {
		let row = get_row(cdt, cdn);
		if (!row) return;

		dbg("expense_account changed | parentfield:", row.parentfield, "| idx:", row.idx, "| item_code:", row.item_code, "| expense_account:", row.expense_account);
		if (row.parentfield === "bundle_items") {
			trigger_bundle_update(frm, "expense_account");
		}
	},

	bundle_items_add(frm, cdt, cdn) {
		let row = get_row(cdt, cdn);
		dbg("bundle_items_add | paste_active:", bundle_paste_active);

		if (row) {
			if (frm.doc.from_warehouse) {
				frappe.model.set_value(cdt, cdn, "s_warehouse", frm.doc.from_warehouse);
				dbg("  → auto-set s_warehouse:", frm.doc.from_warehouse);
			} else {
				dbg_warn("  → from_warehouse not set on doc — s_warehouse skipped");
			}
			if (frm.doc.to_warehouse) {
				frappe.model.set_value(cdt, cdn, "t_warehouse", frm.doc.to_warehouse);
				dbg("  → auto-set t_warehouse:", frm.doc.to_warehouse);
			} else {
				dbg_warn("  → to_warehouse not set on doc — t_warehouse skipped");
			}
		} else {
			dbg_warn("  → row not found in locals for cdn:", cdn);
		}

		if (!bundle_paste_active) {
			trigger_bundle_update(frm, "row_add");
		} else {
			dbg("  → skipping trigger_bundle_update (paste in progress)");
		}
	},

	bundle_items_remove(frm) {
		dbg("bundle_items_remove fired | bundle_items remaining:", (frm.doc.bundle_items || []).length);
		trigger_bundle_update(frm, "row_remove");
	}
});


/* =====================================================
   Helpers
===================================================== */

function get_row(cdt, cdn) {
	return locals[cdt] && locals[cdt][cdn];
}

function set_warehouses(frm) {
	let from = frm.doc.from_warehouse;
	let to = frm.doc.to_warehouse;

	(frm.doc.bundle_items || []).forEach((row) => {
		if (from) {
			frappe.model.set_value(row.doctype, row.name, "s_warehouse", from);
		}
		if (to) {
			frappe.model.set_value(row.doctype, row.name, "t_warehouse", to);
		}
	});
}

/* =====================================================
   Paste Override (bundle_items only)
===================================================== */

function install_bundle_paste_override(frm) {
	const wrapper = frm.fields_dict.bundle_items?.wrapper;
	if (!wrapper) {
		dbg_warn("install_bundle_paste_override: bundle_items wrapper not found — skipping");
		return;
	}

	if (wrapper.__bundle_override_installed) {
		dbg("install_bundle_paste_override: already installed, skipping");
		return;
	}
	wrapper.__bundle_override_installed = true;
	dbg("install_bundle_paste_override: listener attached ✓");

	wrapper.addEventListener(
		"paste",
		function (e) {
			const in_grid_body = !!e.target.closest(".grid-body");
			const in_grid_form = !!e.target.closest(".form-in-grid");

			dbg("paste event captured | in_grid_body:", in_grid_body, "| in_grid_form:", in_grid_form, "| target tag:", e.target.tagName, "| target fieldname:", $(e.target).data("fieldname"));

			if (!in_grid_body) {
				dbg("  → not inside .grid-body, ignoring");
				return;
			}
			if (in_grid_form) {
				dbg("  → inside .form-in-grid (expanded row), ignoring");
				return;
			}

			e.preventDefault();
			e.stopImmediatePropagation();

			const text = frappe.utils.get_clipboard_data(e);
			dbg("  → clipboard text length:", text ? text.length : 0);
			if (!text) {
				dbg_warn("  → empty clipboard, aborting");
				return;
			}

			process_bundle_paste(frm, e.target, text);
		},
		true
	);
}


/* =====================================================
   Bundle Paste — column-aware, fully sequential

   Root cause of previous failures:
   All data rows were scheduled with setTimeout(0) in parallel.
   Frappe's add_new_row() is itself async (it enqueues a model
   update internally), so by the time row N's callback ran,
   frm.doc.bundle_items and grid.grid_rows had not yet reflected
   the row added for row N-1. This caused every other row to see
   a stale table length and fail to resolve row_name.

   Fix: use frappe.run_serially() to process rows one at a time,
   waiting for each set_value (and the add_new_row it may trigger)
   to fully settle before moving to the next row.
===================================================== */

function process_bundle_paste(frm, target_el, text) {
	dbg("─── process_bundle_paste ───────────────────────────");

	let data = frappe.utils.csv_to_array(text, "\t");
	dbg("parsed rows:", data ? data.length : 0, "| first row:", data && data[0]);

	if (!data || !data.length) {
		dbg_warn("  → no data parsed, aborting");
		return;
	}

	if (data.length === 1 && data[0].length === 1) {
		dbg("  → single-cell paste, yielding to native handler");
		return;
	}

	const grid            = frm.fields_dict.bundle_items.grid;
	const doctype         = grid.doctype;
	const grid_pagination = grid.grid_pagination;

	dbg("grid doctype:", doctype, "| grid_rows count (at parse time):", grid.grid_rows ? grid.grid_rows.length : 0);

	if (!grid.grid_rows || !grid.grid_rows.length) {
		dbg_warn("  → no grid_rows found, aborting");
		return;
	}

	const value_formatter_map = {
		Date:     (val) => (val ? frappe.datetime.user_to_str(val) : val),
		Int:      (val) => cint(val),
		Check:    (val) => cint(val),
		Float:    (val) => flt(val),
		Currency: (val) => flt(val),
	};

	// --- Resolve column mapping ---
	let fieldnames = [];
	let fieldtypes = [];

	const first_cell   = data[0][0];
	const header_match = get_bundle_field(grid, first_cell);
	dbg("header detection | first_cell:", JSON.stringify(first_cell), "| resolved fieldname:", header_match);

	if (header_match) {
		dbg("  → mode: HEADER ROW");
		data[0].forEach((col_header) => {
			const fn = get_bundle_field(grid, col_header);
			fieldnames.push(fn);
			const df = frappe.meta.get_docfield(doctype, fn);
			fieldtypes.push(df ? df.fieldtype : "");
			dbg("    col header:", JSON.stringify(col_header), "→ fieldname:", fn, "| fieldtype:", df ? df.fieldtype : "?");
		});
		data.shift();
		dbg("  → header row consumed, remaining data rows:", data.length);
	} else {
		dbg("  → mode: ACTIVE COLUMN");
		const visible_columns  = grid.grid_rows[0].get_visible_columns();
		const target_fieldname = $(target_el).data("fieldname");
		dbg("  → target element fieldname (data-fieldname attr):", target_fieldname);
		dbg("  → visible columns:", visible_columns.map(c => c.fieldname));

		let target_column_matched = false;
		visible_columns.forEach((col) => {
			if (target_column_matched || col.fieldname === target_fieldname) {
				fieldnames.push(col.fieldname);
				const df = frappe.meta.get_docfield(doctype, col.fieldname);
				fieldtypes.push(df ? df.fieldtype : "");
				target_column_matched = true;
			}
		});

		if (!target_column_matched) {
			dbg_warn("  → target column NOT matched — falling back to first visible column");
			visible_columns.forEach((col) => {
				fieldnames.push(col.fieldname);
				const df = frappe.meta.get_docfield(doctype, col.fieldname);
				fieldtypes.push(df ? df.fieldtype : "");
			});
		}
	}

	dbg("final column mapping:", fieldnames.map((fn, i) => fn + " [" + fieldtypes[i] + "]"));

	// --- Starting row ---
	const row_docname = $(target_el).closest(".grid-row").data("name");
	let row_idx = row_docname ? (locals[doctype]?.[row_docname]?.idx || 1) : 1;
	dbg("starting row_docname:", row_docname, "| row_idx:", row_idx);

	const data_length = data.length;
	dbg("rows to write:", data_length);
	dbg_table("clipboard data", data.map((r) => Object.fromEntries(fieldnames.map((fn, j) => [fn || ("col" + j), r[j]]))));

	bundle_paste_active = true;
	dbg("bundle_paste_active = true");

	// Build a task array for frappe.run_serially.
	// Each task is a function that returns a Promise.
	// Running them serially means row N only starts after row N-1's
	// set_value (and any internal async model work it triggered)
	// has fully resolved — so frm.doc.bundle_items and grid.grid_rows
	// are always up to date before we call add_new_row().
	const tasks = data.map((row, i) => {
		return () => {
			return new Promise((resolve) => {
				const blank_row = !row.filter(Boolean).length;
				if (blank_row) {
					dbg("  row", i, "→ blank, skipping");
					resolve();
					return;
				}

				// Always read live state — previous task has settled by now
				const current_length = (frm.doc.bundle_items || []).length;

				if (row_idx > current_length) {
					dbg("  row", i, "→ row_idx", row_idx, "> table length", current_length, ", adding new row");
					grid.add_new_row();
				}

				if (row_idx > 1 && (row_idx - 1) % grid_pagination.page_length === 0) {
					dbg("  row", i, "→ advancing pagination to page", grid_pagination.page_index + 1);
					grid_pagination.go_to_page(grid_pagination.page_index + 1);
				}

				// grid_rows is read fresh after add_new_row()
				const row_name = grid.grid_rows[row_idx - 1]?.doc?.name;
				if (!row_name) {
					dbg_warn("  row", i, "→ could not resolve row_name for row_idx:", row_idx,
						"| grid.grid_rows.length:", grid.grid_rows.length,
						"| frm.doc.bundle_items.length:", (frm.doc.bundle_items || []).length);
					resolve();
					return;
				}

				dbg("  row", i, "→ writing to row_name:", row_name, "| row_idx:", row_idx, "| raw values:", row);

				// Build set_value calls as a serial sub-chain for this row's columns
				const col_tasks = row.map((value, data_index) => {
					return () => {
						if (!fieldnames[data_index]) {
							dbg("    col", data_index, "→ no fieldname mapping, skipping value:", value);
							return Promise.resolve();
						}

						const formatted = value_formatter_map[fieldtypes[data_index]]
							? value_formatter_map[fieldtypes[data_index]](value)
							: value;

						dbg("    col", data_index, "→ fieldname:", fieldnames[data_index], "| raw:", JSON.stringify(value), "| formatted:", JSON.stringify(formatted));
						// frappe.model.set_value returns a Promise
						return frappe.model.set_value(doctype, row_name, fieldnames[data_index], formatted);
					};
				});

				frappe.run_serially(col_tasks).then(() => {
					row_idx++;

					if (data_length >= 10) {
						frappe.show_progress(__("Processing"), i + 1, data_length, null, true);
					}

					resolve();
				});
			});
		};
	});

	frappe.run_serially(tasks).then(() => {
		dbg("all rows written — refreshing bundle_items and triggering rebuild");
		frm.refresh_field("bundle_items");
		bundle_paste_active = false;
		dbg("bundle_paste_active = false");
		trigger_bundle_update(frm, "paste_complete");
	});
}

/**
 * Resolves a column header string to a fieldname within bundle_items.
 * Mirrors ControlTable.get_field() from Frappe core.
 */
function get_bundle_field(grid, field_name) {
	if (!field_name) return undefined;
	const needle = field_name.toLowerCase();
	let matched;

	(grid?.meta?.fields || []).some((field) => {
		if (frappe.model.no_value_type.includes(field.fieldtype)) return false;

		const is_match =
			field.fieldname.toLowerCase() === needle ||
			(field.label || "").toLowerCase() === needle ||
			(__(field.label, null, field.parent) || "").toLowerCase() === needle;

		if (is_match) {
			matched = field.fieldname;
			return true;
		}
	});

	return matched;
}


/* =====================================================
   Bundle Rebuild -> items table
===================================================== */

function trigger_bundle_update(frm, source) {
	dbg("trigger_bundle_update | source:", source, "| paste_active:", bundle_paste_active);

	if (bundle_paste_active) {
		dbg("  → suppressed (paste in progress)");
		return;
	}

	clearTimeout(bundle_timer);
	dbg("  → debounce timer reset, firing in 300ms");

	bundle_timer = setTimeout(() => {
		run_bundle_update(frm, source);
	}, 300);
}

function run_bundle_update(frm, source) {
	let all_rows = frm.doc.bundle_items || [];
	let rows = all_rows.filter(row => row.item_code && flt(row.qty) > 0);

	dbg("─── run_bundle_update ──────────────────────────────");
	dbg("source:", source, "| total bundle_items:", all_rows.length, "| valid rows (has item_code + qty):", rows.length);

	if (rows.length === 0) {
		dbg("  → no valid rows — clearing items table");
		frm.clear_table("items");
		frm.refresh_field("items");
		return;
	}

	dbg_table("bundle rows sent to server", rows.map(r => ({
		item_code: r.item_code,
		qty: r.qty,
		basic_rate: r.basic_rate,
		expense_account: r.expense_account,
		s_warehouse: r.s_warehouse,
		t_warehouse: r.t_warehouse,
	})));

	bundle_request_id++;
	let current = bundle_request_id;
	dbg("  → request_id:", current);

	frappe.call({
		method: "eseller_suite.eseller_suite.custom_script.stock_entry.stock_entry.process_bundle_items",
		args: {
			bundle_items: JSON.stringify(rows),
			from_warehouse: frm.doc.from_warehouse,
			to_warehouse: frm.doc.to_warehouse,
		},
		callback(r) {
			if (current !== bundle_request_id) {
				dbg("  → stale response (request_id", current, "vs current", bundle_request_id, "), discarding");
				return;
			}

			let generated = r.message || [];
			dbg("  → server returned", generated.length, "item rows");
			dbg_table("generated items", generated.map(d => ({
				item_code: d.item_code,
				qty: d.qty,
				basic_rate: d.basic_rate,
				s_warehouse: d.s_warehouse,
				t_warehouse: d.t_warehouse,
			})));

			frm.clear_table("items");
			generated.forEach(d => frm.add_child("items", d));
			frm.refresh_field("items");
			dbg("  → items table updated ✓");
		}
	});
}


/* =====================================================
   Existing Logic
===================================================== */

function restrict_actions_for_amazon_invoice(frm) {
	if (frm.doc.amazon_invoice_id) {
		dbg("amazon_invoice_id present — disabling form");
		frm.disable_form();
		frm.disable_save();
		frm.clear_custom_buttons();
	}
}

function set_filters(frm) {
	dbg("set_filters | company:", frm.doc.company);

	frm.set_query("item_code", "bundle_items", () => ({
		filters: { is_bundle_item: 1 }
	}));

	["s_warehouse", "t_warehouse"].forEach(field => {
		frm.set_query(field, "bundle_items", () => ({
			filters: { company: frm.doc.company }
		}));
	});

	frm.set_query("expense_account", "bundle_items", () => ({
		filters: { company: frm.doc.company }
	}));
}

function fetch_item_details(frm, cdt, cdn) {
	let row = get_row(cdt, cdn);
	if (!row || !row.item_code) return;

	dbg("fetch_item_details | item_code:", row.item_code);

	frappe.call({
		method: "frappe.client.get",
		args: {
			doctype: "Item",
			name: row.item_code
		},
		callback(r) {
			if (!r.message) {
				dbg_warn("fetch_item_details: no message returned for item_code:", row.item_code);
				return;
			}
			dbg("fetch_item_details response | item_name:", r.message.item_name, "| stock_uom:", r.message.stock_uom);
			frappe.model.set_value(cdt, cdn, "item_name", r.message.item_name);
			frappe.model.set_value(cdt, cdn, "description", r.message.description);
			frappe.model.set_value(cdt, cdn, "uom", r.message.stock_uom);
		}
	});
}
