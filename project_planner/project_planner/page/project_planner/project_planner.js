frappe.pages["project-planner"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Project Planner"),
		single_column: true,
	});

	const mount_point = document.createElement("div");
	mount_point.id = "project-planner-root";
	page.main.get(0).appendChild(mount_point);

	const load_app = () => {
		if (!window.ProjectPlanner || !window.ProjectPlanner.mount) {
			frappe.msgprint(__("Project Planner frontend assets are not built. Run the frontend build first."));
			return;
		}
		window.ProjectPlanner.mount(mount_point);
	};

	frappe.require(
		[
			"/assets/project_planner/frontend/project-planner.css",
			"/assets/project_planner/frontend/project-planner.js",
		],
		load_app
	);
};
