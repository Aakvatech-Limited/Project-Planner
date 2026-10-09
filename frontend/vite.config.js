import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
	plugins: [vue()],
	// Vue/frappe-ui includes CommonJS-style NODE_ENV checks. Vite's IIFE library
	// output must replace these at compile time: browsers have no global process.
	define: {
		"process.env.NODE_ENV": JSON.stringify("production"),
	},
	build: {
		outDir: fileURLToPath(new URL("../project_planner/public/frontend", import.meta.url)),
		emptyOutDir: true,
		lib: {
			entry: fileURLToPath(new URL("./src/main.js", import.meta.url)),
			name: "ProjectPlanner",
			formats: ["iife"],
			fileName: () => "project-planner.js",
			cssFileName: "project-planner",
		},
	},
	resolve: {
		alias: {
			"@": root,
		},
	},
});
