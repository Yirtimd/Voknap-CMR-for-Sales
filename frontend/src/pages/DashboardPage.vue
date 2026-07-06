<script setup lang="ts">
import { crmStore } from "../stores/crm";
</script>

<template>
  <section class="stack">
    <div class="metric-grid">
      <div class="metric"><span>Лиды</span><strong>{{ crmStore.leads.value.length }}</strong></div>
      <div class="metric"><span>Сделки</span><strong>{{ crmStore.deals.value.length }}</strong></div>
      <div class="metric"><span>Открытые задачи</span><strong>{{ crmStore.openTasks.value.length }}</strong></div>
      <div class="metric"><span>Пайплайн</span><strong>{{ crmStore.money(crmStore.totalPipeline.value) }}</strong></div>
    </div>

    <div class="section-grid">
      <section class="panel">
        <h2>Быстрый старт</h2>
        <form class="compact-form" @submit.prevent="crmStore.createPipeline">
          <label>Воронка<input v-model="crmStore.pipelineForm.value.name" /></label>
          <label>Этапы<input v-model="crmStore.pipelineForm.value.stages" /></label>
          <button type="submit">Создать</button>
        </form>
      </section>

      <section class="panel">
        <h2>Последние лиды</h2>
        <div v-for="lead in crmStore.leads.value.slice(0, 5)" :key="lead.id" class="list-row">
          <span>{{ lead.title }}</span>
          <small>{{ lead.source ?? "Источник не указан" }}</small>
        </div>
        <p v-if="!crmStore.leads.value.length" class="empty">Лидов пока нет</p>
      </section>
    </div>
  </section>
</template>

