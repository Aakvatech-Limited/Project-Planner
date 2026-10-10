import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, afterEach } from "vitest";
import { FrappeUI } from "frappe-ui";
import App from "../src/App.vue";

vi.mock("../src/components/ProjectLink.vue", () => ({
	default: {
		props: ["modelValue", "disabled"],
		emits: ["update:modelValue"],
		template: `<button data-testid="project" @click="$emit('update:modelValue', 'P')">Choose Project</button>`,
	},
}));

let wrapper;
afterEach(() => { wrapper?.unmount(); document.body.innerHTML = ""; });

async function openPlanner() {
	const rows = ["A", "B", "C"].map((name) => ({ name, subject: `Task ${name}`, duration: 1 }));
	let dependencies = [];
	const call = vi.fn(({ method, args, callback }) => {
		if (method.endsWith("get_project_plan")) {
			callback({ message: { project: { name: "P" }, tasks: rows, dependencies } });
		} else if (method.endsWith("unlink_tasks")) {
			dependencies = [];
			callback({ message: { removed: 1 } });
		} else {
			dependencies = [{ parent: "C", task: "A" }];
			callback({ message: { created: 1 } });
		}
	});
	window.frappe = { call };
	wrapper = mount(App, { attachTo: document.body, global: { plugins: [FrappeUI] } });
	await wrapper.get('[data-testid="project"]').trigger("click");
	await flushPromises();
	return call;
}

describe("Link and Unlink controls", () => {
	it("remain mounted and enable after selecting two actual Frappe UI checkboxes", async () => {
		await openPlanner();
		const link = wrapper.get(".planner-link");
		const unlink = wrapper.get(".planner-unlink");
		expect(link.attributes("disabled")).toBeDefined();
		await wrapper.get('input[aria-label="Select Task A"]').setValue(true);
		expect(link.attributes("disabled")).toBeDefined();
		await wrapper.get('input[aria-label="Select Task C"]').setValue(true);
		expect(link.isVisible()).toBe(true);
		expect(unlink.isVisible()).toBe(true);
		expect(link.attributes("disabled")).toBeUndefined();
		expect(unlink.attributes("disabled")).toBeUndefined();
	});

	it("calls both endpoints and retains selection after linking and unlinking", async () => {
		const call = await openPlanner();
		await wrapper.get('input[aria-label="Select Task C"]').setValue(true);
		await wrapper.get('input[aria-label="Select Task A"]').setValue(true);
		await wrapper.get(".planner-link").trigger("click");
		await flushPromises();
		expect(call).toHaveBeenCalledWith(expect.objectContaining({
			method: "project_planner.api.link_tasks",
			args: { project: "P", tasks: ["A", "C"], dependency_type: "FS (Finish-to-Start)", lag_days: 0 },
		}));
		expect(wrapper.get('input[aria-label="Select Task A"]').element.checked).toBe(true);
		expect(wrapper.get(".planner-unlink").attributes("disabled")).toBeUndefined();
		await wrapper.get(".planner-unlink").trigger("click");
		await flushPromises();
		expect(call).toHaveBeenCalledWith(expect.objectContaining({
			method: "project_planner.api.unlink_tasks", args: { project: "P", tasks: ["A", "C"] },
		}));
		expect(wrapper.get(".planner-link").isVisible()).toBe(true);
		expect(wrapper.get('input[aria-label="Select Task C"]').element.checked).toBe(true);
	});
});
