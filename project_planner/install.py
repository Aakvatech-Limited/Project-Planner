"""Ensure the Vue/Vite frontend exists for fresh and existing installations.

The generated assets belong to the bench's shared app directory, not to any
individual site. Only build when a required output is missing or empty.
"""

import subprocess
from pathlib import Path


def _missing_frontend_assets(app_root):
	output = app_root / "project_planner" / "public" / "frontend"
	return [
		filename
		for filename in ("project-planner.js", "style.css")
		if not (output / filename).is_file() or (output / filename).stat().st_size == 0
	]


def ensure_frontend_assets():
	"""Build missing frontend assets on install and after migrate.

	Do not build on normal migrations if both expected files already exist.
	A failed npm command propagates the exception instead of hiding a broken UI.
	"""
	app_root = Path(__file__).resolve().parent.parent
	if not _missing_frontend_assets(app_root):
		return

	subprocess.run(["npm", "run", "build"], cwd=app_root, check=True)
	missing = _missing_frontend_assets(app_root)
	if missing:
		raise RuntimeError(
			"Project Planner frontend build did not create: " + ", ".join(missing)
		)
