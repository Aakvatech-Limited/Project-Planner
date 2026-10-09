"""Regression tests for repeatable Project Planner schema reconciliation."""

from types import SimpleNamespace
from unittest.mock import call, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from project_planner import custom_fields


class TestCustomFieldReconciliation(FrappeTestCase):
    def test_dependency_fields_are_exported(self):
        exported = custom_fields._load_fields()
        dependency_fields = {field["fieldname"] for field in exported["Task Depends On"]}
        self.assertTrue(
            set(custom_fields.REQUIRED_FIELDS["Task Depends On"]) <= dependency_fields
        )

    def test_insert_after_order_is_stable(self):
        fields = [
            {"fieldname": "child", "insert_after": "parent"},
            {"fieldname": "parent", "insert_after": "task"},
        ]
        ordered = custom_fields._ordered_fields(fields)
        self.assertEqual([field["fieldname"] for field in ordered], ["parent", "child"])

    def test_cycle_in_field_order_fails(self):
        with patch.object(frappe, "throw", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                custom_fields._ordered_fields([
                    {"fieldname": "a", "insert_after": "b"},
                    {"fieldname": "b", "insert_after": "a"},
                ])

    def test_missing_database_column_fails_after_schema_sync(self):
        fields = {
            "Task Depends On": [
                {"fieldname": "custom_dependency_type", "fieldtype": "Select", "insert_after": "task"},
                {"fieldname": "custom_lag_or_lead_days", "fieldtype": "Int",
                 "insert_after": "custom_dependency_type"},
            ]
        }
        db_meta = SimpleNamespace(fieldtype="Select", is_virtual=False)
        with (
            patch.object(custom_fields, "_load_fields", return_value=fields),
            patch.object(frappe, "get_doc", return_value=SimpleNamespace(fields=[])),
            patch.object(frappe.db, "get_value", side_effect=lambda *args, **kwargs:
                db_meta if kwargs.get("as_dict") else None),
            patch.object(frappe.db, "updatedb") as updatedb,
            patch.object(frappe.db, "has_column", return_value=False),
            patch.object(custom_fields, "create_custom_fields") as create_fields,
            patch.object(frappe, "clear_cache"),
            patch.object(frappe, "throw", side_effect=RuntimeError),
        ):
            with self.assertRaisesRegex(RuntimeError, "could not create database column"):
                custom_fields.execute()
            create_fields.assert_called_once()
            updatedb.assert_called_once_with("Task Depends On")

    def test_reconcile_repairs_schema_with_existing_metadata(self):
        fields = {"Task Depends On": [
            {"fieldname": "custom_dependency_type", "fieldtype": "Select", "insert_after": "task"},
            {"fieldname": "custom_lag_or_lead_days", "fieldtype": "Int",
             "insert_after": "custom_dependency_type"},
        ]}
        db_meta = SimpleNamespace(fieldtype="Select", is_virtual=False)
        with (
            patch.object(custom_fields, "_load_fields", return_value=fields),
            patch.object(frappe, "get_doc", return_value=SimpleNamespace(fields=[])),
            patch.object(frappe.db, "get_value", return_value=db_meta),
            patch.object(frappe.db, "updatedb") as updatedb,
            patch.object(frappe.db, "has_column", return_value=True),
            patch.object(custom_fields, "create_custom_fields") as create_fields,
            patch.object(frappe, "clear_cache"),
        ):
            custom_fields.execute()
            self.assertEqual(create_fields.call_count, 1)
            updatedb.assert_has_calls([call("Task Depends On")])
