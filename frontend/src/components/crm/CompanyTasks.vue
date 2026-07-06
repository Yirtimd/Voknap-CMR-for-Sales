<script setup lang="ts">
import type { CompanyWorkspace } from "../../types";

defineProps<{ workspace: CompanyWorkspace }>();
</script>

<template>
  <section class="panel">
    <h2>Tasks</h2>
    <div v-for="task in workspace.tasks" :key="task.id" class="list-row">
      <span :class="{ done: task.done_at }">{{ task.title }}</span>
      <small>{{ task.done_at ? "done" : "open" }}</small>
    </div>
    <p v-if="!workspace.tasks.length" class="empty">No tasks yet</p>
  </section>
</template>

