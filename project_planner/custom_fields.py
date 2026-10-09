"""Reconcile Project Planner-owned Custom Fields on install and migration.

The exported JSON is the source of truth. Standard ERPNext fields are not replaced.
"""

import json
from pathlib import Path

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


FIELD_FILES = (
    "project_custom_fields.json",
    "task_custom_fields.json",
    "task_depends_on_custom_fields.json",
)
SYSTEM_FIELDS = {
    "name", "doctype", "owner", "creation", "modified", "modified_by",
    "docstatus", "idx", "is_system_generated", "__last_sync_on",
}
NO_COLUMN_TYPES = {
    "Button", "Column Break", "Section Break", "Tab Break",
    "HTML", "Heading", "Fold",
}
REQUIRED_FIELDS = {
    "Task Depends On": ("custom_dependency_type", "custom_lag_or_lead_days"),
}


def _ordered_fields(fields):
    """Create fields after their exported custom-field anchors."""
    pending = {field["fieldname"]: field for field in fields}
    ordered = []
    while pending:
        progress = False
        for name, field in list(pending.items()):
            if field.get("insert_after") not in pending:
                ordered.append(field)
                del pending[name]
                progress = True
        if not progress:
            frappe.throw(
                "Project Planner Custom Field definitions have cyclic insert_after references: "
                + ", ".join(sorted(pending))
            )
    return ordered


def _load_fields():
    data_dir = Path(frappe.get_app_path("project_planner", "patches", "v0_0", "data"))
    valid_columns = set(frappe.get_meta("Custom Field").get_valid_columns())
    result = {}
    for filename in FIELD_FILES:
        with (data_dir / filename).open(encoding="utf-8") as source:
            rows = json.load(source)
        for row in rows:
            doctype = row["dt"]
            if not frappe.db.exists("DocType", doctype):
                frappe.throw(f"Project Planner requires missing DocType {doctype}")
            field = {
                key: value for key, value in row.items()
                if key in valid_columns and key not in SYSTEM_FIELDS
            }
            if not field.get("fieldname") or not field.get("fieldtype"):
                frappe.throw(f"Invalid Project Planner Custom Field definition in {filename}")
            result.setdefault(doctype, []).append(field)
    return result


def _reconcile_fields():
    fields_by_doctype = _load_fields()
    for doctype, fields in fields_by_doctype.items():
        # An ERPNext release can turn a formerly custom field into a standard one.
        standard_fields = {field.fieldname for field in frappe.get_doc("DocType", doctype).fields}
        custom_fields = []
        for field in fields:
            name = field["fieldname"]
            existing = frappe.db.get_value(
                "Custom Field", {"dt": doctype, "fieldname": name}, "name"
            )
            if name in standard_fields:
                if existing:
                    frappe.throw(
                        f"Project Planner field {doctype}.{name} conflicts with a standard field"
                    )
                continue
            custom_fields.append(field)
        if custom_fields:
            create_custom_fields({doctype: _ordered_fields(custom_fields)}, update=True)
        frappe.clear_cache(doctype=doctype)
        # Existing metadata can be intact even when the physical table lost a column.
        frappe.db.updatedb(doctype)

    for doctype, fieldnames in REQUIRED_FIELDS.items():
        for fieldname in fieldnames:
            metadata = frappe.db.get_value(
                "Custom Field", {"dt": doctype, "fieldname": fieldname},
                ["fieldtype", "is_virtual"], as_dict=True,
            )
            if not metadata:
                frappe.throw(f"Project Planner requires Custom Field {doctype}.{fieldname}")
            if not metadata.is_virtual and metadata.fieldtype not in NO_COLUMN_TYPES:
                if not frappe.db.has_column(doctype, fieldname):
                    frappe.throw(
                        f"Project Planner could not create database column {doctype}.{fieldname}"
                    )


def execute():
    _reconcile_fields()
