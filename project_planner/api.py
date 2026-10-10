import json

import frappe
from frappe import _


@frappe.whitelist()
def get_project_plan(project: str):
	frappe.has_permission("Project", "read", doc=project, throw=True)

	project_doc = frappe.get_doc("Project", project)
	tasks = frappe.get_list(
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
			"custom_planner_sequence",
		],
		order_by="custom_planner_sequence asc, creation asc",
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
	if dependency_type not in (
		"FS (Finish-to-Start)", "SS (Start-to-Start)",
		"FF (Finish-to-Finish)", "SF (Start-to-Finish)",
	):
		frappe.throw(_("Invalid dependency type."))

	created = 0
	skipped = 0

	for predecessor_name, successor_name in zip(task_names, task_names[1:]):
		if predecessor_name == successor_name:
			frappe.throw(_("A task cannot be linked to itself."))

		successor = frappe.get_doc("Task", successor_name)
		frappe.has_permission("Task", "write", doc=successor, throw=True)
		frappe.has_permission("Task", "read", doc=predecessor_name, throw=True)

		existing = next((row for row in successor.depends_on if row.task == predecessor_name), None)
		if existing:
			skipped += 1
			continue

		successor.append(
			"depends_on",
			{
				"task": predecessor_name,
				"subject": frappe.db.get_value("Task", predecessor_name, "subject"),
				"project": project,
				"custom_dependency_type": dependency_type,
				"custom_lag_or_lead_days": frappe.utils.cint(lag_days),
			},
		)
		successor.save()
		created += 1

	return {"created": created, "skipped": skipped}


@frappe.whitelist()
def unlink_tasks(project: str, tasks):
	task_names = _parse_task_names(tasks)
	if len(task_names) < 2:
		frappe.throw(_("Select at least two tasks to unlink."))

	_validate_project_tasks(project, task_names)

	removed = 0

	# Remove existing edges among selected tasks, regardless of display order.
	# This also permits unlinking rows created using the old successor convention.
	selected = set(task_names)
	docs = [frappe.get_doc("Task", name) for name in task_names]
	changes = [
		(doc, [row for row in doc.depends_on if row.task not in selected])
		for doc in docs
		if any(row.task in selected for row in doc.depends_on)
	]
	for doc, rows in changes:
		doc.check_permission("write")
	for doc, rows in changes:
		removed += len(doc.depends_on) - len(rows)
		doc.set("depends_on", rows)
		doc.save()

	return {"removed": removed}


def _parse_task_names(tasks):
	if isinstance(tasks, str):
		tasks = json.loads(tasks)

	return list(dict.fromkeys(str(task).strip() for task in (tasks or []) if str(task).strip()))


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


@frappe.whitelist()
def update_duration(project: str, task: str, duration):
	_validate_project_tasks(project, [task])
	doc = frappe.get_doc("Task", task)
	doc.check_permission("write")
	try:
		value = float(duration)
	except (TypeError, ValueError):
		frappe.throw(_("Duration must be a non-negative whole number of days."))
	if not value >= 0 or not value.is_integer() or value > 365000:
		frappe.throw(_("Duration must be a non-negative whole number of days."))
	doc.duration = int(value)
	if doc.exp_start_date:
		doc.exp_end_date = frappe.utils.add_days(doc.exp_start_date, max(doc.duration - 1, 0))
	doc.save()
	return {"name": doc.name}


@frappe.whitelist()
def reorder_tasks(project: str, tasks):
	names = _parse_task_names(tasks)
	_validate_project_tasks(project, names)
	# Only update the planner's display sequence; never change Task hierarchy or dependencies.
	docs = [frappe.get_doc("Task", name) for name in names]
	for doc in docs:
		doc.check_permission("write")
	for index, doc in enumerate(docs, 1):
		doc.custom_planner_sequence = index
		doc.save()
	return {"updated": len(docs)}


@frappe.whitelist()
def insert_task(project: str, subject: str, before_task=None, duration=1):
	frappe.has_permission("Project", "write", doc=project, throw=True)
	if not subject or not subject.strip():
		frappe.throw(_("Task Name is required."))
	anchor = None
	if before_task:
		_validate_project_tasks(project, [before_task])
		anchor = frappe.get_doc("Task", before_task)
		anchor.check_permission("read")
	value = frappe.utils.cint(duration)
	if value < 0:
		frappe.throw(_("Duration cannot be negative."))
	doc = frappe.get_doc({
		"doctype": "Task", "project": project, "subject": subject.strip(),
		"parent_task": anchor.parent_task if anchor else None,
		"duration": value,
		"custom_planner_sequence": anchor.custom_planner_sequence if anchor else 0,
	})
	names = frappe.get_list(
		"Task", filters={"project": project}, pluck="name",
		order_by="custom_planner_sequence asc, creation asc", limit_page_length=5000,
	)
	doc.insert()
	index = names.index(before_task) if before_task else len(names)
	names.insert(index, doc.name)
	reorder_tasks(project, names)
	return {"name": doc.name}


@frappe.whitelist()
def delete_tasks(project: str, tasks):
	names = _parse_task_names(tasks)
	_validate_project_tasks(project, names)
	docs = [frappe.get_doc("Task", name) for name in names]
	for doc in docs:
		doc.check_permission("delete")
	# Children are removed first. Standard link checks protect referenced records.
	for doc in sorted(docs, key=lambda doc: doc.lft or 0, reverse=True):
		frappe.delete_doc("Task", doc.name)
	return {"deleted": len(docs)}
