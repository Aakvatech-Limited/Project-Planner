app_name = "project_planner"
app_title = "Project Planner"
app_publisher = "Aakvatech"
app_description = "MS Project-style planning enhancements for ERPNext Project and Task"
app_email = "info@aakvatech.com"
app_license = "MIT"

required_apps = ["erpnext"]

# Asset output is shared across sites on a bench. The helper checks for
# missing/empty assets before invoking npm, including on older installations.
after_install = "project_planner.install.ensure_frontend_assets"
after_migrate = "project_planner.install.ensure_frontend_assets"

add_to_apps_screen = [
	{
		"name": "project_planner",
		"title": "Project Planner",
		"route": "/app/project-planner",
	}
]
