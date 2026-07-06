<script setup lang="ts">
import type { CompanyWorkspace } from "../../types";

defineProps<{ workspace: CompanyWorkspace }>();
</script>

<template>
  <section class="panel wide">
    <h2>Timeline</h2>
    <article v-for="activity in workspace.activities" :key="String(activity.id)" class="timeline-item">
      <span class="timeline-icon">{{ String(activity.type).slice(0, 2) }}</span>
      <div>
        <header>
          <strong>{{ activity.title }}</strong>
          <small>{{ activity.type }}</small>
        </header>
        <p v-if="activity.description">{{ activity.description }}</p>
      </div>
    </article>
    <p v-if="!workspace.activities.length" class="empty">Timeline is empty</p>
  </section>
</template>

