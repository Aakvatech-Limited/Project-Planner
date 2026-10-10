<template>
	<Combobox
		v-model="value"
		v-model:query="query"
		:options="options"
		:disabled="disabled"
		:loading="resource.loading"
		:filterable="false"
		placeholder="Select Project"
		@update:open="onOpen"
	/>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Combobox, createResource } from "frappe-ui";

const props = defineProps({
	modelValue: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const query = ref("");
let debounceTimer = null;

const value = computed({
	get: () => props.modelValue || null,
	set: (next) => emit("update:modelValue", next || ""),
});

const resource = createResource({
	url: "frappe.desk.search.search_link",
	method: "POST",
	params: {
		txt: "",
		doctype: "Project",
		page_length: 30,
	},
	transform(data) {
		return (data || []).map((row) => ({
			value: row.value,
			label: row.label || row.value,
			description: row.description,
		}));
	},
});

const options = computed(() => {
	const rows = resource.data || [];
	if (value.value && !rows.some((row) => row.value === value.value)) {
		return [{ value: value.value, label: value.value }, ...rows];
	}
	return rows;
});

function reload() {
	resource.update({
		params: {
			txt: query.value || "",
			doctype: "Project",
			page_length: 30,
		},
	});
	resource.reload();
}

function onOpen(open) {
	if (open) {
		query.value = "";
		reload();
	}
}

watch(query, () => {
	clearTimeout(debounceTimer);
	debounceTimer = setTimeout(reload, 250);
});

reload();
</script>
