<script setup lang="ts">
import { computed } from "vue";

import type { CompanyWorkspace } from "../../types";
import { crmStore } from "../../stores/crm";

const props = defineProps<{ workspace: CompanyWorkspace }>();
const emit = defineEmits<{
  action: [value: "call" | "email" | "meeting" | "task"];
}>();

const openTasks = computed(() => props.workspace.tasks.filter((task) => !task.done_at).length);
const health = computed(() => Math.min(98, 70 + props.workspace.contacts.length * 4 + props.workspace.deals.length * 6));
</script>

<template>
  <section class="company-header">
    <div class="company-title-block">
      <RouterLink class="secondary-link close-workspace" to="/companies">Companies</RouterLink>
      <p class="eyebrow">Workspace Modal</p>
      <h1>{{ workspace.company.name }}</h1>
      <p>{{ workspace.company.industry ?? "B2B" }}</p>
      <div class="company-health-bar" aria-label="Company health">
        <span :style="{ width: `${health}%` }"></span>
      </div>
      <div class="quick-actions">
        <button type="button" @click="emit('action', 'call')">Call</button>
        <button class="secondary" type="button" @click="emit('action', 'email')">Generate Email</button>
        <button class="secondary" type="button" @click="emit('action', 'meeting')">Meeting</button>
        <button class="secondary" type="button" @click="emit('action', 'task')">Task</button>
      </div>
    </div>
    <dl class="workspace-kpis">
      <div><dt>Health</dt><dd>{{ health }}</dd></div>
      <div><dt>Revenue</dt><dd>{{ crmStore.money(Number(workspace.overview.pipeline_amount ?? 0)) }}</dd></div>
      <div><dt>Open Tasks</dt><dd>{{ openTasks }}</dd></div>
      <div><dt>Owner</dt><dd>Sales</dd></div>
    </dl>
  </section>
</template>
