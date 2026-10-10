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

async function openPlanner(options = {}) {
	const rows = ["A", "B", "C"].map((name) => ({ name, subject: `Task ${name}`, duration: 1, exp_start_date: "2026-10-10 08:30:00", exp_end_date: "2026-10-12 17:00:00" }));
	let dependencies = options.dependencies || [];
	const call = vi.fn(({ method, args, callback, error }) => {
		if (options.fail && method.endsWith("link_tasks")) { error(new Error("Permission denied")); return; }
		if (method.endsWith("get_project_plan")) {
			callback({ message: { project: { name: "P" }, tasks: rows, dependencies } });
		} else if (method.endsWith("unlink_tasks")) {
			dependencies = [];
			callback({ message: options.unlinkResult || { removed: 1 } });
		} else {
			dependencies = [{ parent: "C", task: "A" }];
			if (options.changeSchedule) rows[2].exp_start_date = "2026-10-13 08:30:00";
			callback({ message: options.linkResult || { created: 1 } });
		}
	});
	window.frappe = { call, show_alert: vi.fn(), utils: { get_form_link: (doctype, name) => `/desk/task/${encodeURIComponent(name)}` } };
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

	it("shows persistent created and removed results plus actual schedule changes", async () => {
		await openPlanner({ changeSchedule: true, linkResult: { created: 1, skipped: 0, details: [{ predecessor: "A", successor: "C", status: "created" }] } });
		await wrapper.get('input[aria-label="Select Task A"]').setValue(true);
		await wrapper.get('input[aria-label="Select Task C"]').setValue(true);
		await wrapper.get(".planner-link").trigger("click");
		await flushPromises();
		expect(wrapper.get(".planner-action-result").text()).toContain("1 created; 0 already existed");
		expect(wrapper.get(".planner-action-result").text()).toContain("Task A (A) → Task C (C): Linked");
		expect(wrapper.get(".planner-action-result").text()).toContain("1 task schedules changed");
		expect(window.frappe.show_alert).toHaveBeenCalled();
		await wrapper.get(".planner-unlink").trigger("click");
		await flushPromises();
		expect(wrapper.get(".planner-action-result").text()).toContain("1 existing dependencies removed");
	});

	it("explains existing links and unlink with nothing to remove", async () => {
		await openPlanner({ linkResult: { created: 0, skipped: 1 }, unlinkResult: { removed: 0 } });
		await wrapper.get('input[aria-label="Select Task A"]').setValue(true);
		await wrapper.get('input[aria-label="Select Task C"]').setValue(true);
		await wrapper.get(".planner-link").trigger("click");
		await flushPromises();
		expect(wrapper.get(".planner-action-result").text()).toContain("0 created; 1 already existed (unchanged)");
		await wrapper.get(".planner-unlink").trigger("click");
		await flushPromises();
		expect(wrapper.get(".planner-action-result").text()).toContain("no dependency existed");
	});

	it("shows errors instead of reporting a successful link", async () => {
		await openPlanner({ fail: true });
		await wrapper.get('input[aria-label="Select Task A"]').setValue(true);
		await wrapper.get('input[aria-label="Select Task C"]').setValue(true);
		await wrapper.get(".planner-link").trigger("click");
		await flushPromises();
		expect(wrapper.get(".planner-action-result").text()).toContain("Link failed: Permission denied");
	});

	it("renders clickable task and both dependency columns before dates, with no time", async () => {
		await openPlanner({ dependencies: [{ parent: "C", task: "A", custom_dependency_type: "FS (Finish-to-Start)", custom_lag_or_lead_days: 2 }] });
		const headers = wrapper.findAll("th").map((cell) => cell.text());
		expect(headers.indexOf("Predecessors")).toBeLessThan(headers.indexOf("Start"));
		expect(headers.indexOf("Successors")).toBeLessThan(headers.indexOf("Start"));
		const rows = wrapper.findAll("tbody tr");
		expect(rows[0].findAll("td")[4].text()).toContain("Task C (C)");
		expect(rows[2].findAll("td")[3].text()).toContain("Task A (A)");
		expect(rows[2].findAll("td")[3].text()).toContain("FS +2d");
		expect(rows[0].findAll("td")[5].text()).toBe("2026-10-10");
		expect(rows[0].findAll("td")[6].text()).toBe("2026-10-12");
		expect(rows[0].get("a").attributes()).toMatchObject({ href: "/desk/task/A", target: "_blank", rel: "noopener noreferrer" });
		expect(wrapper.get(".planner-scheduling-notice").text()).toContain("can change task start/finish dates and times");
	});

});
