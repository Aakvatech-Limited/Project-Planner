"""Planner regression tests without a running ERPNext bench."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class Task:
	def __init__(self, name, dependencies=()):
		self.name = name
		self.depends_on = [types.SimpleNamespace(task=name) for name in dependencies]
		self.save = Mock()
		self.check_permission = Mock()
		self.exp_start_date = None
		self.lft = 0

	def append(self, field, values):
		getattr(self, field).append(types.SimpleNamespace(**values))

	def set(self, field, values):
		setattr(self, field, values)


class PlannerAPITests(unittest.TestCase):
	def setUp(self):
		self.frappe = types.ModuleType("frappe")
		self.frappe.whitelist = lambda: lambda function: function
		self.frappe._ = lambda value: value
		self.frappe.has_permission = Mock()
		self.frappe.get_all = Mock(return_value=["A", "B", "C"])
		self.frappe.db = types.SimpleNamespace(get_value=Mock(return_value="Task subject"))
		self.frappe.utils = types.SimpleNamespace(cint=int, add_days=Mock(return_value="2026-10-12"))
		self.frappe.throw = Mock(side_effect=ValueError)
		self.docs = {name: Task(name) for name in ("A", "B", "C")}
		self.frappe.get_doc = Mock(side_effect=lambda doctype, name: self.docs[name])
		path = Path(__file__).resolve().parents[1] / "project_planner" / "api.py"
		spec = importlib.util.spec_from_file_location("planner_api_test", path)
		self.api = importlib.util.module_from_spec(spec)
		with patch.dict(sys.modules, {"frappe": self.frappe}):
			spec.loader.exec_module(self.api)

	def test_link_chain_stores_predecessors_on_successors(self):
		result = self.api.link_tasks("P", ["A", "B", "C"], lag_days=2)
		self.assertEqual((result["created"], result["skipped"]), (2, 0))
		self.assertEqual([row["status"] for row in result["details"]], ["created", "created"])
		self.assertEqual(self.docs["A"].depends_on, [])
		self.assertEqual(self.docs["B"].depends_on[0].task, "A")
		self.assertEqual(self.docs["C"].depends_on[0].task, "B")
		self.assertEqual(self.docs["C"].depends_on[0].custom_lag_or_lead_days, 2)

	def test_link_is_idempotent(self):
		self.api.link_tasks("P", ["A", "B"])
		result = self.api.link_tasks("P", ["A", "B"])
		self.assertEqual((result["created"], result["skipped"]), (0, 1))
		self.assertEqual(result["details"], [{"predecessor": "A", "successor": "B", "status": "existing"}])

	def test_unlink_preserves_other_predecessors(self):
		self.docs["B"] = Task("B", ["A", "C"])
		result = self.api.unlink_tasks("P", ["A", "B"])
		self.assertEqual(result["removed"], 1)
		self.assertEqual(result["details"], [{"predecessor": "A", "successor": "B", "status": "removed"}])
		self.assertEqual([row.task for row in self.docs["B"].depends_on], ["C"])

	def test_unlink_removes_nonadjacent_and_reverse_edges(self):
		self.docs["A"] = Task("A", ["C"])
		self.docs["C"] = Task("C", ["B", "EXTERNAL"])
		self.assertEqual(self.api.unlink_tasks("P", ["C", "A", "B"])["removed"], 2)
		self.assertEqual(self.docs["A"].depends_on, [])
		self.assertEqual([row.task for row in self.docs["C"].depends_on], ["EXTERNAL"])

	def test_unlink_checks_all_write_permissions_before_saving(self):
		self.docs["B"] = Task("B", ["A"])
		self.docs["C"] = Task("C", ["B"])
		self.docs["C"].check_permission.side_effect = PermissionError
		with self.assertRaises(PermissionError):
			self.api.unlink_tasks("P", ["A", "B", "C"])
		self.docs["B"].save.assert_not_called()

	def test_unlink_reports_no_existing_dependencies(self):
		self.assertEqual(self.api.unlink_tasks("P", ["A", "B"]), {"removed": 0, "details": []})

	def test_duration_updates_finish_and_saves(self):
		self.docs["A"].exp_start_date = "2026-10-10"
		self.api.update_duration("P", "A", 3)
		self.frappe.utils.add_days.assert_called_once_with("2026-10-10", 2)
		self.assertEqual(self.docs["A"].duration, 3)
		self.docs["A"].save.assert_called_once()
		self.docs["A"].check_permission.assert_called_once_with("write")

	def test_invalid_duration_does_not_save(self):
		for value in (-1, 1.5, "invalid", "NaN", "Infinity"):
			with self.subTest(value=value), self.assertRaises(ValueError):
				self.api.update_duration("P", "A", value)
		self.docs["A"].save.assert_not_called()

	def test_reorder_checks_all_permissions_before_saving(self):
		self.docs["B"].check_permission.side_effect = PermissionError
		with self.assertRaises(PermissionError):
			self.api.reorder_tasks("P", ["A", "B"])
		self.docs["A"].save.assert_not_called()

	def test_reorder_persists_sequence_without_changing_dependencies(self):
		self.api.reorder_tasks("P", ["C", "A", "B"])
		self.assertEqual([self.docs[name].custom_planner_sequence for name in ("C", "A", "B")], [1, 2, 3])
		self.assertTrue(all(not doc.depends_on for doc in self.docs.values()))

	def test_insert_before_creates_sibling_and_persists_order(self):
		self.docs["B"].parent_task = "Group"
		self.docs["B"].custom_planner_sequence = 2
		new_task = Task("NEW")
		new_task.insert = Mock()
		self.frappe.get_list = Mock(return_value=["A", "B", "C"])
		self.frappe.get_doc.side_effect = lambda doctype, name=None: new_task if isinstance(doctype, dict) else self.docs[name]
		self.api.reorder_tasks = Mock()
		result = self.api.insert_task("P", "New task", before_task="B")
		self.assertEqual(result, {"name": "NEW"})
		values = self.frappe.get_doc.call_args_list[-1].args[0]
		self.assertEqual(values["parent_task"], "Group")
		new_task.insert.assert_called_once()
		self.api.reorder_tasks.assert_called_once_with("P", ["A", "NEW", "B", "C"])

	def test_delete_uses_standard_checks_and_children_first(self):
		self.docs["A"].lft = 1
		self.docs["B"].lft = 2
		self.frappe.delete_doc = Mock()
		self.api.delete_tasks("P", ["A", "B"])
		self.assertEqual([call.args for call in self.frappe.delete_doc.call_args_list], [("Task", "B"), ("Task", "A")])


if __name__ == "__main__":
	unittest.main()
