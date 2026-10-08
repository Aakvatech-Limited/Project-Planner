import json

import frappe
from frappe import _


@frappe.whitelist()
def get_project_plan(project: str):
	frappe.has_permission("Project", "read", doc=project, throw=True)

	project_doc = frappe.get_doc("Project", project)
	tasks = frappe.get_all(
		"Task",
		filters={"project": project},
		fields=[
			"name",
			"subject",
			"parent_task",
			"is_group",
			"is_milestone",
			"status",
			"priority",
			"exp_start_date",
			"exp_end_date",
			"progress",
			"duration",
		],
		order_by="creation asc",
		limit_page_length=5000,
	)

	task_names = [task.name for task in tasks]
	dependencies = []

	if task_names:
		dependencies = frappe.get_all(
			"Task Depends On",
			filters={
				"parenttype": "Task",
				"parentfield": "depends_on",
				"parent": ["in", task_names],
			},
			fields=[
				"name",
				"parent",
				"task",
				"subject",
				"project",
				"custom_dependency_type",
				"custom_lag_or_lead_days",
			],
			order_by="idx asc",
			limit_page_length=10000,
		)

	return {
		"project": {
			"name": project_doc.name,
			"project_name": project_doc.project_name,
			"custom_project_number_": project_doc.get("custom_project_number_"),
			"expected_start_date": project_doc.expected_start_date,
			"expected_end_date": project_doc.expected_end_date,
		},
		"tasks": tasks,
		"dependencies": dependencies,
	}


@frappe.whitelist()
def link_tasks(project: str, tasks, dependency_type="FS (Finish-to-Start)", lag_days=0):
	task_names = _parse_task_names(tasks)
	if len(task_names) < 2:
		frappe.throw(_("Select at least two tasks to link."))

	_validate_project_tasks(project, task_names)

	created = 0
	skipped = 0

	for predecessor_name, successor_name in zip(task_names, task_names[1:]):
		if predecessor_name == successor_name:
			frappe.throw(_("A task cannot be linked to itself."))

		predecessor = frappe.get_doc("Task", predecessor_name)
		frappe.has_permission("Task", "write", doc=predecessor, throw=True)

		existing = next((row for row in predecessor.depends_on if row.task == successor_name), None)
		if existing:
			skipped += 1
			continue

		successor_subject = frappe.db.get_value("Task", successor_name, "subject")
		predecessor.append(
			"depends_on",
			{
				"task": successor_name,
				"subject": successor_subject,
				"project": project,
				"custom_dependency_type": dependency_type,
				"custom_lag_or_lead_days": frappe.utils.cint(lag_days),
			},
		)
		predecessor.save()
		created += 1

	return {"created": created, "skipped": skipped}


@frappe.whitelist()
def unlink_tasks(project: str, tasks):
	task_names = _parse_task_names(tasks)
	if len(task_names) < 2:
		frappe.throw(_("Select at least two tasks to unlink."))

	_validate_project_tasks(project, task_names)

	removed = 0

	for predecessor_name, successor_name in zip(task_names, task_names[1:]):
		predecessor = frappe.get_doc("Task", predecessor_name)
		frappe.has_permission("Task", "write", doc=predecessor, throw=True)

		before = len(predecessor.depends_on)
		predecessor.set("depends_on", [row for row in predecessor.depends_on if row.task != successor_name])

		if len(predecessor.depends_on) != before:
			predecessor.save()
			removed += 1

	return {"removed": removed}


def _parse_task_names(tasks):
	if isinstance(tasks, str):
		tasks = json.loads(tasks)

	return [str(task).strip() for task in (tasks or []) if str(task).strip()]


def _validate_project_tasks(project, task_names):
	frappe.has_permission("Project", "read", doc=project, throw=True)

	found = frappe.get_all(
		"Task",
		filters={"project": project, "name": ["in", task_names]},
		pluck="name",
		limit_page_length=len(task_names),
	)

	missing = [task for task in task_names if task not in found]
	if missing:
		frappe.throw(_("Tasks not found in project {0}: {1}").format(project, ", ".join(missing)))
