<template>
	<div class="flex h-full flex-col gap-3 p-3">
		<div class="project-planner-toolbar flex flex-wrap items-end gap-2 rounded-lg border p-3">
			<div class="w-[420px] max-w-full">
				<div class="mb-1 text-sm font-medium text-ink-gray-8">Project</div>
				<ProjectLink v-model="project" />
			</div>

			<Button
				label="Refresh"
				variant="subtle"
				:disabled="!project || loading"
				@click="loadPlan"
			/>

			<div class="mx-1 hidden h-8 w-px bg-outline-gray-2 md:block" />

			<Button
				label="Link"
				variant="solid"
				:disabled="selectedTasks.length < 2 || busy"
				@click="linkSelected"
			/>
			<Button
				label="Unlink"
				variant="subtle"
				:disabled="selectedTasks.length < 2 || busy"
				@click="unlinkSelected"
			/>

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
				{{ projectData.expected_start_date || "No start" }}
				→
				{{ projectData.expected_end_date || "No finish" }}
			</span>
		</div>

		<div v-if="selectedTasks.length" class="rounded-md border bg-surface-gray-1 px-3 py-2 text-sm">
			<span class="font-medium">Link sequence:</span>
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
								@update:model-value="toggleAll"
							/>
						</th>
						<th class="w-14">#</th>
						<th>Task Name</th>
						<th>Start</th>
						<th>Finish</th>
						<th>Duration</th>
						<th>Status</th>
						<th>Successors</th>
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
								<strong v-if="entry.task.is_group">{{ entry.task.subject }}</strong>
								<span v-else>{{ entry.task.subject }}</span>
								<span class="ml-2 text-xs text-ink-gray-4">{{ entry.task.name }}</span>
							</div>
						</td>
						<td>{{ entry.task.exp_start_date || "" }}</td>
						<td>{{ entry.task.exp_end_date || "" }}</td>
						<td>{{ entry.task.duration || "" }}</td>
						<td>{{ entry.task.status || "" }}</td>
						<td>
							<span v-if="successorsFor(entry.task.name).length">
								{{ successorsFor(entry.task.name).join(", ") }}
							</span>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { Badge, Button, Checkbox, FormControl, toast } from "frappe-ui";
import { deskCall } from "./deskApi";
import ProjectLink from "./components/ProjectLink.vue";

const project = ref("");
const projectData = ref(null);
const tasks = ref([]);
const dependencies = ref([]);
const loading = ref(false);
const busy = ref(false);
const selected = reactive({});

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
	clearSelection();
	if (value) loadPlan();
	else {
		projectData.value = null;
		tasks.value = [];
		dependencies.value = [];
	}
});

async function loadPlan() {
	if (!project.value) return;

	loading.value = true;
	try {
		const data = await deskCall("project_planner.api.get_project_plan", {
			project: project.value,
		});
		projectData.value = data.project;
		tasks.value = data.tasks || [];
		dependencies.value = data.dependencies || [];
		clearSelection();
	} catch (error) {
		toast.error(error?.message || "Unable to load project plan");
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

function successorsFor(taskName) {
	return dependencies.value
		.filter((row) => row.parent === taskName)
		.map((row) => row.task);
}

async function linkSelected() {
	if (selectedTasks.value.length < 2) return;
	busy.value = true;

	try {
		const result = await deskCall("project_planner.api.link_tasks", {
			project: project.value,
			tasks: selectedTasks.value.map((task) => task.name),
			dependency_type: dependencyType.value,
			lag_days: Number(lagDays.value || 0),
		});
		toast.success(
			`${result.created || 0} dependencies created` +
				(result.skipped ? `; ${result.skipped} already existed` : "")
		);
		await loadPlan();
	} catch (error) {
		toast.error(error?.message || "Unable to link tasks");
	} finally {
		busy.value = false;
	}
}

async function unlinkSelected() {
	if (selectedTasks.value.length < 2) return;
	busy.value = true;

	try {
		const result = await deskCall("project_planner.api.unlink_tasks", {
			project: project.value,
			tasks: selectedTasks.value.map((task) => task.name),
		});
		toast.success(`${result.removed || 0} dependencies removed`);
		await loadPlan();
	} catch (error) {
		toast.error(error?.message || "Unable to unlink tasks");
	} finally {
		busy.value = false;
	}
}
</script>
