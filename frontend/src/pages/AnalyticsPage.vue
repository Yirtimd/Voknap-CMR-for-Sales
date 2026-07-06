<script setup lang="ts">
import { computed, onMounted } from "vue";

import { crmStore } from "../stores/crm";

onMounted(() => {
  void crmStore.refreshAll();
});

const wonDeals = computed(() => crmStore.deals.value.filter((deal) => deal.status === "won"));
const openDeals = computed(() => crmStore.deals.value.filter((deal) => deal.status !== "won"));
const avgDeal = computed(() => crmStore.deals.value.length ? crmStore.totalPipeline.value / crmStore.deals.value.length : 0);
</script>

<template>
  <section class="stack">
    <div class="metric-grid">
      <div class="metric">
        <span>Companies</span>
        <strong>{{ crmStore.companies.value.length }}</strong>
      </div>
      <div class="metric">
        <span>Open pipeline</span>
        <strong>{{ crmStore.money(crmStore.totalPipeline.value) }}</strong>
      </div>
      <div class="metric">
        <span>Open deals</span>
        <strong>{{ openDeals.length }}</strong>
      </div>
      <div class="metric">
        <span>Average deal</span>
        <strong>{{ crmStore.money(avgDeal) }}</strong>
      </div>
    </div>

    <section class="section-grid">
      <section class="panel">
        <h2>Forecast</h2>
        <article v-for="column in crmStore.dealsByStage.value" :key="column.stage.id" class="list-row">
          <span>{{ column.stage.name }}</span>
          <small>{{ column.deals.length }} / {{ crmStore.money(column.amount) }}</small>
        </article>
      </section>

      <section class="panel">
        <h2>Execution</h2>
        <article class="list-row">
          <span>Open tasks</span>
          <small>{{ crmStore.openTasks.value.length }}</small>
        </article>
        <article class="list-row">
          <span>Won deals</span>
          <small>{{ wonDeals.length }}</small>
        </article>
      </section>
    </section>
  </section>
</template>
