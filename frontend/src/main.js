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
