<template>
	<div class="flex h-full flex-col gap-3 p-3">
		<div class="project-planner-toolbar flex flex-wrap items-end gap-2 rounded-lg border p-3">
			<div class="w-[420px] max-w-full">
				<div class="mb-1 text-sm font-medium text-ink-gray-8">Project</div>
				<ProjectLink v-model="project" :disabled="busy || loading" />
			</div>

			<Button
				label="Refresh"
				variant="subtle"
				:disabled="!project || loading"
				@click="loadPlan()"
			/>

			<div class="mx-1 hidden h-8 w-px bg-outline-gray-2 md:block" />

			<div class="planner-dependency-actions flex w-full flex-wrap items-end gap-2">
			<button class="btn btn-primary btn-sm planner-link" :disabled="selectedTasks.length < 2 || busy || loading" @click="linkSelected">Link</button>
			<button class="btn btn-default btn-sm planner-unlink" :disabled="selectedTasks.length < 2 || busy || loading" @click="unlinkSelected">Unlink</button>
			<Button label="Add Row" :disabled="!project || busy || loading" @click="insertRow()" />
			<Button label="Insert Row" :disabled="selectedTasks.length !== 1 || busy || loading" @click="insertRow(selectedTasks[0])" />
			<Button label="Delete Rows" :disabled="!selectedTasks.length || busy || loading" @click="deleteRows" />

			<div class="w-52">
				<FormControl
					v-model="dependencyType"
					type="select"
					label="Dependency Type"
					:options="dependencyOptions"
				/>
			</div>

			<div class="w-36">
				<FormControl
					v-model="lagDays"
					type="number"
					label="Lag / Lead"
				/>
			</div>

			</div>

			<div class="ml-auto flex items-center gap-2">
				<Badge v-if="selectedTasks.length" :label="selectedTasks.length + ' selected'" />
				<Button
					label="Clear"
					variant="ghost"
					:disabled="!selectedTasks.length"
					@click="clearSelection"
				/>
			</div>
		</div>

		<div v-if="projectData" class="flex flex-wrap items-center gap-2 px-1 text-sm">
			<strong>{{ projectData.project_name || projectData.name }}</strong>
			<Badge
				v-if="projectData.custom_project_number_"
				:label="projectData.custom_project_number_"
				theme="gray"
			/>
			<span class="text-ink-gray-5">
				{{ displayDate(projectData.expected_start_date) || "No start" }}
				→
				{{ displayDate(projectData.expected_end_date) || "No finish" }}
			</span>
		</div>

		<p class="px-1 text-sm text-ink-gray-6" role="status">
			Select at least two task checkboxes. Link creates a chain in grid order;
			Unlink removes existing dependencies between the selected tasks, in either direction.
		</p>

		<div class="planner-scheduling-notice rounded-md border px-3 py-2 text-sm">
			<strong>Dependencies affect scheduling.</strong>
			Saving a dependency runs ERPNext Task validation and scheduling hooks, which can change task start/finish dates and times.
			Existing links are left unchanged. Unlink does not restore previous dates.
			Dependency type and lag/lead scheduling depends on the installed scheduling hooks.
		</div>

		<div v-if="actionResult" class="planner-action-result rounded-md border px-3 py-2 text-sm" :class="{ 'is-error': actionResult.error }" role="status" aria-live="polite">
			<strong>{{ actionResult.message }}</strong>
			<p v-if="actionResult.scheduleMessage">{{ actionResult.scheduleMessage }}</p>
			<ul v-if="actionResult.details?.length">
				<li v-for="(detail, index) in actionResult.details" :key="index">
					{{ taskLabel(detail.predecessor) }} → {{ taskLabel(detail.successor) }}:
					{{ detail.status === 'created' ? 'Linked' : detail.status === 'existing' ? 'Already linked; unchanged' : 'Unlinked' }}
				</li>
			</ul>
		</div>

		<div v-if="selectedTasks.length" class="rounded-md border bg-surface-gray-1 px-3 py-2 text-sm">
			<span class="font-medium">Link sequence (grid order):</span>
			<span v-for="(task, index) in selectedTasks" :key="task.name">
				<span v-if="index" class="mx-2 text-ink-gray-5">→</span>
				{{ task.subject || task.name }}
			</span>
		</div>

		<div class="project-planner-grid min-h-[420px] flex-1">
			<div v-if="loading" class="p-10 text-center text-ink-gray-5">Loading project plan…</div>
			<div v-else-if="!project" class="p-10 text-center text-ink-gray-5">
				Select a project to begin planning.
			</div>
			<div v-else-if="!orderedTasks.length" class="p-10 text-center text-ink-gray-5">
				No tasks found for this project.
			</div>

			<table v-else>
				<thead>
					<tr>
						<th class="w-10">
							<Checkbox
								:model-value="allSelected"
								:indeterminate="selectedTasks.length > 0 && !allSelected"
								:disabled="busy || loading"
								aria-label="Select all tasks"
								@update:model-value="toggleAll"
							/>
						</th>
						<th class="w-14">#</th>
						<th>Task Name</th>
						<th class="planner-relations">Predecessors</th>
						<th class="planner-relations">Successors</th>
						<th>Start</th>
						<th>Finish</th>
						<th>Duration (days)</th>
						<th>Status</th>
						<th>Sequence</th>
					</tr>
				</thead>

				<tbody>
					<tr
						v-for="(entry, index) in orderedTasks"
						:key="entry.task.name"
						:class="{ 'is-selected': selected[entry.task.name] }"
					>
						<td>
							<Checkbox
								:model-value="Boolean(selected[entry.task.name])"
								:disabled="busy || loading"
								:aria-label="'Select ' + entry.task.subject"
								@update:model-value="(value) => setSelected(entry.task.name, value)"
							/>
						</td>
						<td>{{ index + 1 }}</td>
						<td>
							<div
								class="flex items-center gap-1"
								:style="{ paddingLeft: entry.level * 18 + 'px' }"
							>
								<span v-if="entry.task.is_group" class="text-ink-gray-5">▸</span>
								<a class="planner-task-link" :href="taskUrl(entry.task.name)" target="_blank" rel="noopener noreferrer"
									:class="{ 'font-semibold': entry.task.is_group }" :title="'Open ' + entry.task.name + ' in a new tab'">
									{{ entry.task.subject || entry.task.name }}
								</a>
								<span class="ml-2 text-xs text-ink-gray-4">{{ entry.task.name }}</span>
							</div>
						</td>
						<td class="planner-relations">
							<div v-for="row in predecessorsFor(entry.task.name)" :key="row.name || row.parent + row.task">
								<a class="planner-task-link" :href="taskUrl(row.task)" target="_blank" rel="noopener noreferrer">{{ taskLabel(row.task) }}</a>
								<span class="text-ink-gray-5"> · {{ relationshipLabel(row) }}</span>
							</div>
							<span v-if="!predecessorsFor(entry.task.name).length" class="text-ink-gray-5">—</span>
						</td>
						<td class="planner-relations">
							<div v-for="row in successorsFor(entry.task.name)" :key="row.name || row.parent + row.task">
								<a class="planner-task-link" :href="taskUrl(row.parent)" target="_blank" rel="noopener noreferrer">{{ taskLabel(row.parent) }}</a>
								<span class="text-ink-gray-5"> · {{ relationshipLabel(row) }}</span>
							</div>
							<span v-if="!successorsFor(entry.task.name).length" class="text-ink-gray-5">—</span>
						</td>
						<td>{{ displayDate(entry.task.exp_start_date) }}</td>
						<td>{{ displayDate(entry.task.exp_end_date) }}</td>
						<td class="w-32">
							<FormControl type="number" :model-value="entry.task.duration ?? 0" min="0" step="1"
								:disabled="busy || loading" :aria-label="'Duration for ' + entry.task.subject"
								@change="(event) => saveDuration(entry.task, event.target.value)" />
						</td>
						<td>{{ entry.task.status || "" }}</td>
						<td class="flex gap-1">
							<Button label="↑" :aria-label="'Move ' + entry.task.subject + ' up'" :disabled="busy || loading || !canMove(entry.task, -1)" @click="moveRow(entry.task, -1)" />
							<Button label="↓" :aria-label="'Move ' + entry.task.subject + ' down'" :disabled="busy || loading || !canMove(entry.task, 1)" @click="moveRow(entry.task, 1)" />
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { Badge, Button, Checkbox, FormControl } from "frappe-ui";
import { deskCall } from "./deskApi";
import ProjectLink from "./components/ProjectLink.vue";

const project = ref("");
const projectData = ref(null);
const tasks = ref([]);
const dependencies = ref([]);
const loading = ref(false);
const busy = ref(false);
const selected = reactive({});
const actionResult = ref(null);

const dependencyType = ref("FS (Finish-to-Start)");
const lagDays = ref(0);

const dependencyOptions = [
	"FS (Finish-to-Start)",
	"SS (Start-to-Start)",
	"FF (Finish-to-Finish)",
	"SF (Start-to-Finish)",
];

const orderedTasks = computed(() => {
	const byParent = new Map();
	const known = new Set(tasks.value.map((task) => task.name));

	for (const task of tasks.value) {
		const key = task.parent_task || "__ROOT__";
		if (!byParent.has(key)) byParent.set(key, []);
		byParent.get(key).push(task);
	}

	const roots = tasks.value.filter(
		(task) => !task.parent_task || !known.has(task.parent_task)
	);
	const result = [];

	function add(task, level) {
		result.push({ task, level });
		for (const child of byParent.get(task.name) || []) add(child, level + 1);
	}

	for (const root of roots) add(root, 0);
	return result;
});

const selectedTasks = computed(() =>
	orderedTasks.value
		.map((entry) => entry.task)
		.filter((task) => selected[task.name])
);

const allSelected = computed(
	() => orderedTasks.value.length > 0 && selectedTasks.value.length === orderedTasks.value.length
);

watch(project, (value) => {
	actionResult.value = null;
	clearSelection();
	if (value) loadPlan();
	else {
		projectData.value = null;
		tasks.value = [];
		dependencies.value = [];
	}
});

async function loadPlan(preserveSelection = false) {
	if (!project.value) return;

	loading.value = true;
	try {
		const data = await deskCall("project_planner.api.get_project_plan", {
			project: project.value,
		});
		projectData.value = data.project;
		tasks.value = data.tasks || [];
		dependencies.value = data.dependencies || [];
		if (!preserveSelection) clearSelection();
		else {
			const known = new Set(tasks.value.map((task) => task.name));
			for (const name of Object.keys(selected)) if (!known.has(name)) delete selected[name];
		}
		return true;
	} catch (error) {
		notify(error?.message || "Unable to load project plan", true);
		return false;
	} finally {
		loading.value = false;
	}
}

function setSelected(taskName, value) {
	if (value) selected[taskName] = true;
	else delete selected[taskName];
}

function toggleAll(value) {
	clearSelection();
	if (value) {
		for (const entry of orderedTasks.value) selected[entry.task.name] = true;
	}
}

function clearSelection() {
	for (const key of Object.keys(selected)) delete selected[key];
}

function displayDate(value) {
	if (!value) return "";
	const date = String(value).slice(0, 10);
	return window.frappe?.datetime?.str_to_user?.(date) || date;
}

function taskUrl(name) {
	return window.frappe?.utils?.get_form_link?.("Task", name) || `/app/task/${encodeURIComponent(name)}`;
}

function taskLabel(name) {
	const task = tasks.value.find((row) => row.name === name);
	return task?.subject ? `${task.subject} (${name})` : name;
}

function relationshipLabel(row) {
	const type = (row.custom_dependency_type || "FS").split(" ")[0];
	const lag = Number(row.custom_lag_or_lead_days || 0);
	return type + (lag ? ` ${lag > 0 ? "+" : ""}${lag}d` : "");
}

function predecessorsFor(taskName) {
	return dependencies.value.filter((row) => row.parent === taskName);
}

function successorsFor(taskName) {
	return dependencies.value.filter((row) => row.task === taskName);
}

function notify(message, error = false) {
	const safeMessage = String(message).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
	window.frappe?.show_alert?.({ message: safeMessage, indicator: error ? "red" : "green" }, 7);
}

async function changeDependencies(action) {
	if (selectedTasks.value.length < 2 || busy.value || loading.value) return;
	busy.value = true;
	actionResult.value = { message: action === "link" ? "Linking selected tasks…" : "Unlinking selected tasks…" };
	const before = new Map(tasks.value.map((task) => [task.name, [task.exp_start_date, task.exp_end_date]]));
	try {
		const args = { project: project.value, tasks: selectedTasks.value.map((task) => task.name) };
		if (action === "link") {
			args.dependency_type = dependencyType.value;
			args.lag_days = Number(lagDays.value || 0);
		}
		const result = await deskCall(`project_planner.api.${action}_tasks`, args);
		const message = action === "link"
			? `Link: ${result.created || 0} created; ${result.skipped || 0} already existed (unchanged).`
			: result.removed
				? `Unlink: ${result.removed} existing dependencies removed.`
				: "Unlink: no dependency existed between the selected tasks; nothing was removed.";
		const refreshed = await loadPlan(true);
		const changed = tasks.value.filter((task) => {
			const dates = before.get(task.name);
			return dates && (dates[0] !== task.exp_start_date || dates[1] !== task.exp_end_date);
		}).length;
		actionResult.value = {
			message, details: result.details || [],
			scheduleMessage: refreshed
				? changed ? `${changed} task schedules changed. Review Start and Finish below.` : "No start/finish changes were detected in the loaded tasks."
				: "Dependencies were saved, but the schedule could not be refreshed. Click Refresh to review dates.",
		};
		notify(message);
	} catch (error) {
		const message = `${action === "link" ? "Link" : "Unlink"} failed: ${error?.message || "Unable to save dependencies"}`;
		actionResult.value = { message, error: true };
		notify(message, true);
	} finally {
		busy.value = false;
	}
}

async function linkSelected() { await changeDependencies("link"); }
async function unlinkSelected() { await changeDependencies("unlink"); }

async function mutate(method, args) {
	busy.value = true;
	try {
		const result = await deskCall(`project_planner.api.${method}`, { project: project.value, ...args });
		await loadPlan(true);
		return result;
	} catch (error) {
		notify(error?.message || "Unable to save changes", true);
		await loadPlan(true);
	} finally {
		busy.value = false;
	}
}

async function saveDuration(task, value) {
	if (Number(value) === Number(task.duration)) return;
	await mutate("update_duration", { task: task.name, duration: value });
}

function siblings(task) {
	return tasks.value.filter((row) => (row.parent_task || "") === (task.parent_task || ""));
}

function canMove(task, direction) {
	const rows = siblings(task);
	const index = rows.findIndex((row) => row.name === task.name) + direction;
	return index >= 0 && index < rows.length;
}

async function moveRow(task, direction) {
	if (!canMove(task, direction)) return;
	const rows = [...tasks.value];
	const group = siblings(task);
	const index = group.findIndex((row) => row.name === task.name);
	const other = group[index + direction];
	const a = rows.findIndex((row) => row.name === task.name);
	const b = rows.findIndex((row) => row.name === other.name);
	[rows[a], rows[b]] = [rows[b], rows[a]];
	await mutate("reorder_tasks", { tasks: rows.map((row) => row.name) });
}

function insertRow(beforeTask = null) {
	const currentProject = project.value;
	const dialog = new window.frappe.ui.Dialog({
		title: beforeTask ? "Insert Task Before " + beforeTask.subject : "Add Task",
		fields: [
			{ fieldname: "subject", label: "Task Name", fieldtype: "Data", reqd: 1 },
			{ fieldname: "duration", label: "Duration (days)", fieldtype: "Int", default: 1, reqd: 1 },
		],
		primary_action_label: "Insert",
		async primary_action(values) {
			if (currentProject !== project.value || busy.value) return;
			const result = await mutate("insert_task", { ...values, before_task: beforeTask?.name });
			if (!result) return;
			dialog.hide();
		},
	});
	dialog.show();
}

function deleteRows() {
	const names = selectedTasks.value.map((task) => task.name);
	const currentProject = project.value;
	window.frappe.confirm(`Delete ${names.length} selected task(s)? ERPNext link checks apply.`, async () => {
		if (currentProject !== project.value || busy.value) return;
		await mutate("delete_tasks", { tasks: names });
	});
}

</script>
