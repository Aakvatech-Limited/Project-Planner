// Load Project Planner's Vite assets with explicit error handling. Frappe's
// require() intentionally resolves even when a script or stylesheet returns 404.
frappe.pages["project-planner"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Project Planner"),
		single_column: true,
	});

	const mount_point = document.createElement("div");
	mount_point.id = "project-planner-root";
	page.main.get(0).appendChild(mount_point);

	const asset_version = encodeURIComponent(window._version_number || "");
	const asset_url = (name) =>
		"/assets/project_planner/frontend/" + name + (asset_version ? "?v=" + asset_version : "");

	const load_asset = (url, type) =>
		new Promise((resolve, reject) => {
			const element = document.createElement(type === "css" ? "link" : "script");
			if (type === "css") {
				element.rel = "stylesheet";
				element.href = url;
			} else {
				element.src = url;
				element.async = true;
			}
			element.onload = resolve;
			element.onerror = () => reject(new Error("Unable to load " + url));
			document.head.appendChild(element);
		});

	const mount_app = async () => {
		try {
			// The IIFE may already be loaded on a previous Desk visit.
			await load_asset(asset_url("style.css"), "css");
			if (!window.ProjectPlanner || typeof window.ProjectPlanner.mount !== "function") {
				await load_asset(asset_url("project-planner.js"), "js");
			}
			if (!window.ProjectPlanner || typeof window.ProjectPlanner.mount !== "function") {
				throw new Error(
					"JavaScript loaded but window.ProjectPlanner.mount is unavailable. Check the browser console for a runtime error."
				);
			}
			window.ProjectPlanner.mount(mount_point);
		} catch (error) {
			console.error("Project Planner frontend failed to load:", error);
			frappe.msgprint({
				title: __("Project Planner failed to load"),
				message: __("The frontend could not be loaded. Check the browser developer console and Network tab for the failing asset."),
				indicator: "red",
			});
		}
	};

	mount_app();
};
