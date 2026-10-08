import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

export default defineConfig({
	plugins: [vue()],
	build: {
		outDir: path.resolve(__dirname, "../project_planner/public/frontend"),
		emptyOutDir: true,
		lib: {
			entry: path.resolve(__dirname, "src/main.js"),
			name: "ProjectPlanner",
			formats: ["iife"],
			fileName: () => "project-planner.js",
			cssFileName: "project-planner",
		},
	},
});
