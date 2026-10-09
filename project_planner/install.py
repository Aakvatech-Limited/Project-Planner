"""Install-time fallback for Project Planner's frontend assets.

Bench's normal asset-build lifecycle is preferred. This hook covers installations
where the nested Vite frontend has not yet been compiled.
"""

import subprocess
from pathlib import Path


def ensure_frontend_assets():
	app_root = Path(__file__).resolve().parent.parent
	bundle = app_root / "project_planner" / "public" / "frontend" / "project-planner.js"
	if bundle.is_file() and bundle.stat().st_size > 0:
		return

	# Run the same root-level build entrypoint used by Bench and CI.
	# check=True deliberately fails installation if frontend compilation fails.
	subprocess.run(["npm", "run", "build"], cwd=app_root, check=True)
	if not bundle.is_file() or bundle.stat().st_size == 0:
		raise RuntimeError("Project Planner frontend build did not create project-planner.js")
