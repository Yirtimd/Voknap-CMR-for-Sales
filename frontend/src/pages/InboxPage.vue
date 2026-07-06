<script setup lang="ts">
import { onMounted } from "vue";

import { crmStore } from "../stores/crm";

onMounted(async () => {
  await Promise.allSettled([crmStore.refreshActivities(), crmStore.refreshConnectors()]);
});
</script>

<template>
  <section class="section-grid">
    <section class="panel">
      <h2>Communication Hub</h2>
      <article v-for="activity in crmStore.activities.value.slice(0, 10)" :key="activity.id" class="timeline-item">
        <span class="timeline-icon">{{ activity.type.slice(0, 2) }}</span>
        <div>
          <header>
            <strong>{{ activity.title }}</strong>
            <small>{{ activity.type }}</small>
          </header>
          <p v-if="activity.description">{{ activity.description }}</p>
        </div>
      </article>
      <p v-if="!crmStore.activities.value.length" class="empty">Входящих событий пока нет</p>
    </section>

    <section class="panel">
      <h2>Connector Runs</h2>
      <article v-for="run in crmStore.connectorRuns.value.slice(0, 10)" :key="run.id" class="list-row">
        <span>{{ run.direction }} / {{ run.status }}</span>
        <small>{{ run.created_count }} created</small>
      </article>
      <p v-if="!crmStore.connectorRuns.value.length" class="empty">Синхронизаций пока нет</p>
    </section>
  </section>
</template>
