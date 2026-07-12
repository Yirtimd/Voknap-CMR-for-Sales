<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { CompanyWorkspace } from "../../types";
import { crmStore } from "../../stores/crm";

const props = defineProps<{ workspace: CompanyWorkspace }>();
const showEditor = ref(false);
const title = ref("");
const dueAt = ref("");

const action = computed(() => props.workspace.next_action);
const fallback = computed(() => {
  const task = props.workspace.tasks.find((item) => !item.done_at);
  if (task) return task.title;
  if (!props.workspace.contacts.length) return "Add decision maker contact";
  if (!props.workspace.deals.length) return "Create first opportunity";
  return "Review company timeline and schedule follow-up";
});
const primaryInsight = computed(() =>
  props.workspace.ai_insights[0] ?? "Сфокусироваться на ближайшем контакте."
);

watch(
  () => props.workspace.next_action,
  (value) => {
    title.value = value?.title ?? fallback.value;
    dueAt.value = value?.due_at?.slice(0, 16) ?? "";
  },
  { immediate: true }
);

async function save() {
  if (action.value) await crmStore.toggleNextAction(action.value, true);
  await crmStore.createNextAction({
    company_id: props.workspace.company.id,
    deal_id: props.workspace.deals[0]?.id ?? "",
    contact_id: props.workspace.contacts[0]?.id ?? "",
    title: title.value,
    due_at: dueAt.value,
    priority: "high",
    source: "manual"
  });
  showEditor.value = false;
}

function complete() {
  if (action.value) void crmStore.toggleNextAction(action.value, true);
}
</script>

<template>
  <section class="panel next-action ai-recommendation">
    <p class="eyebrow">Следующее действие</p>
    <h2>{{ action?.title ?? fallback }}</h2>
    <p>{{ action?.description ?? primaryInsight }}</p>
    <small v-if="action?.due_at">Срок: {{ new Date(action.due_at).toLocaleString("ru-RU") }}</small>

    <form v-if="showEditor" class="compact-form" @submit.prevent="save">
      <label>Действие<input v-model="title" required minlength="2" /></label>
      <label>Срок<input v-model="dueAt" type="datetime-local" /></label>
      <div class="button-row">
        <button type="submit" :disabled="crmStore.isLoading.value">Сохранить</button>
        <button class="secondary" type="button" @click="showEditor = false">Отмена</button>
      </div>
    </form>

    <div v-else class="button-row">
      <button v-if="action" type="button" :disabled="crmStore.isLoading.value" @click="complete">Выполнено</button>
      <button class="secondary" type="button" @click="showEditor = true">
        {{ action ? "Заменить" : "Создать" }}
      </button>
    </div>
  </section>
</template>
