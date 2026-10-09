import { createApp } from "vue";
import { FrappeUI, frappeRequest, setConfig } from "frappe-ui";
import App from "./App.vue";
import "./index.css";

setConfig("resourceFetcher", frappeRequest);

export function mount(element) {
	const app = createApp(App);
	app.use(FrappeUI);
	app.mount(element);
	return app;
}

// Frappe Desk loads this IIFE asynchronously. Publish the mount API explicitly
// instead of relying solely on the bundler's inferred global export.
if (typeof window !== "undefined") {
	window.ProjectPlanner = { mount };
}
