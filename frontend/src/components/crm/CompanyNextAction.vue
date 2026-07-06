<script setup lang="ts">
import { computed } from "vue";
import type { CompanyWorkspace } from "../../types";

const props = defineProps<{ workspace: CompanyWorkspace }>();

const nextAction = computed(() => {
  const task = props.workspace.tasks.find((item) => !item.done_at);
  if (task) return task.title;
  if (!props.workspace.contacts.length) return "Add decision maker contact";
  if (!props.workspace.deals.length) return "Create first opportunity";
  return "Review company timeline and schedule follow-up";
});

const primaryInsight = computed(() => props.workspace.ai_insights[0] ?? "Сфокусироваться на ближайшем контакте и зафиксировать следующий шаг.");
</script>

<template>
  <section class="panel next-action ai-recommendation">
    <p class="eyebrow">AI рекомендует</p>
    <h2>{{ nextAction }}</h2>
    <p>{{ primaryInsight }}</p>
    <div class="button-row">
      <button type="button">Call</button>
      <button class="secondary" type="button">Meeting</button>
    </div>
  </section>
</template>
