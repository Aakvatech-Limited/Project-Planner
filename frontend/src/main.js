import { createApp } from "vue";
import { FrappeUI, setConfig } from "frappe-ui";
import { deskResourceFetcher } from "./deskApi";
import App from "./App.vue";
import "./index.css";

setConfig("resourceFetcher", deskResourceFetcher);

export function mount(element) {
	const app = createApp(App);
	app.use(FrappeUI);
	app.mount(element);
	return app;
}

if (typeof window !== "undefined") {
	window.ProjectPlanner = { mount };
}
