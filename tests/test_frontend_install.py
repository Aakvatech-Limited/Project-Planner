"""Tests for missing-frontend recovery without running npm."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from project_planner import install


class FrontendAssetTests(unittest.TestCase):
	def test_both_assets_present(self):
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			output = root / "project_planner" / "public" / "frontend"
			output.mkdir(parents=True)
			(output / "project-planner.js").write_text("js")
			(output / "project-planner.css").write_text("css")
			self.assertEqual(install._missing_frontend_assets(root), [])

	def test_missing_or_empty_assets(self):
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			output = root / "project_planner" / "public" / "frontend"
			output.mkdir(parents=True)
			(output / "project-planner.js").write_text("js")
			(output / "project-planner.css").touch()
			self.assertEqual(install._missing_frontend_assets(root), ["project-planner.css"])

	def test_existing_assets_skip_build(self):
		root = Path(install.__file__).resolve().parent.parent
		with patch.object(install, "_missing_frontend_assets", return_value=[]):
			with patch.object(install.subprocess, "run") as run:
				install.ensure_frontend_assets()
				run.assert_not_called()

	def test_missing_assets_trigger_build(self):
		with patch.object(
			install, "_missing_frontend_assets", side_effect=[["project-planner.js"], []]
		):
			with patch.object(install.subprocess, "run") as run:
				install.ensure_frontend_assets()
				run.assert_called_once()
				self.assertEqual(run.call_args.args[0], ["npm", "run", "build"])
				self.assertTrue(run.call_args.kwargs["check"])

	def test_missing_after_build_fails(self):
		with patch.object(
			install, "_missing_frontend_assets",
			side_effect=[["project-planner.css"], ["project-planner.css"]],
		):
			with patch.object(install.subprocess, "run"):
				with self.assertRaisesRegex(RuntimeError, "project-planner.css"):
					install.ensure_frontend_assets()


if __name__ == "__main__":
	unittest.main()
