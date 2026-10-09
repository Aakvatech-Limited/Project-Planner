app_name = "project_planner"
app_title = "Project Planner"
app_publisher = "Aakvatech"
app_description = "MS Project-style planning enhancements for ERPNext Project and Task"
app_email = "info@aakvatech.com"
app_license = "MIT"

required_apps = ["erpnext"]

# A fresh site installation can precede the bench's asset build. Build only
# when the frontend entry bundle is missing; normal upgrades use bench build.
after_install = "project_planner.install.ensure_frontend_assets"

add_to_apps_screen = [
	{
		"name": "project_planner",
		"title": "Project Planner",
		"route": "/app/project-planner",
	}
]
