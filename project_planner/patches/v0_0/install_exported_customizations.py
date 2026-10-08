import json
from pathlib import Path

import frappe
from frappe.custom.doctype.property_setter.property_setter import (
	delete_property_setter,
	make_property_setter,
)


SYSTEM_FIELDS = {
	"creation",
	"modified",
	"modified_by",
	"owner",
	"docstatus",
	"idx",
}


def execute():
	data_dir = Path(frappe.get_app_path("project_planner", "patches", "v0_0", "data"))

	for filename, doctype in (
		("project_custom_fields.json", "Custom Field"),
		("task_custom_fields.json", "Custom Field"),
		("task_depends_on_custom_fields.json", "Custom Field"),
		("project_property_setters.json", "Property Setter"),
		("task_property_setters.json", "Property Setter"),
		("task_depends_on_property_setters.json", "Property Setter"),
	):
		_upsert_rows(data_dir / filename, doctype)

	_ensure_project_number_search_field()
	_fix_task_field_order()

	for doctype in ("Project", "Task", "Task Depends On"):
		frappe.clear_cache(doctype=doctype)


def _upsert_rows(path: Path, doctype: str):
	with path.open(encoding="utf-8") as handle:
		rows = json.load(handle)

	for row in rows:
		payload = {key: value for key, value in row.items() if key not in SYSTEM_FIELDS}
		payload["doctype"] = doctype
		name = payload.get("name")

		if name and frappe.db.exists(doctype, name):
			doc = frappe.get_doc(doctype, name)
			doc.update({key: value for key, value in payload.items() if key not in {"doctype", "name"}})
			doc.flags.ignore_permissions = True
			doc.save()
		else:
			doc = frappe.get_doc(payload)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_if_duplicate=True)


def _ensure_project_number_search_field():
	search_fields = frappe.db.get_value("DocType", "Project", "search_fields") or ""
	fields = [field.strip() for field in search_fields.split(",") if field.strip()]

	for fieldname in ("custom_project_number_", "project_name"):
		if fieldname not in fields:
			fields.append(fieldname)

	delete_property_setter("Project", "search_fields")

	make_property_setter(
		"Project",
		None,
		"search_fields",
		", ".join(fields),
		"Data",
		for_doctype=True,
		validate_fields_for_doctype=False,
		is_system_generated=False,
	)


def _fix_task_field_order():
	name = "Task-main-field_order"
	if not frappe.db.exists("Property Setter", name):
		return

	setter = frappe.get_doc("Property Setter", name)
	value = setter.value or ""

	if '"duration_test"' in value and '"custom_duration_test"' not in value:
		setter.value = value.replace('"duration_test"', '"custom_duration_test"')
		setter.flags.ignore_permissions = True
		setter.save()
