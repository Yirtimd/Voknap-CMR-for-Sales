<script setup lang="ts">
import { computed, ref } from "vue";

import DealDrawer from "../components/crm/DealDrawer.vue";
import type { Deal } from "../types";
import { crmStore } from "../stores/crm";

const mode = ref<"kanban" | "table" | "list" | "forecast">("kanban");
const selectedDeal = ref<Deal | null>(null);

const modes = [
  { code: "kanban", label: "Kanban" },
  { code: "table", label: "Table" },
  { code: "list", label: "List" },
  { code: "forecast", label: "Forecast" }
] as const;

const forecast = computed(() =>
  crmStore.dealsByStage.value.map((column, index) => ({
    ...column,
    probability: Math.max(20, 80 - index * 15),
    weighted: column.amount * (Math.max(20, 80 - index * 15) / 100)
  }))
);

function companyName(companyId: string) {
  return crmStore.companies.value.find((company) => company.id === companyId)?.name ?? "Company";
}

function stageIndex(stageId: string) {
  return Math.max(0, crmStore.allStages.value.findIndex((stage) => stage.id === stageId));
}

function probability(deal: Deal) {
  const total = Math.max(1, crmStore.allStages.value.length);
  return Math.min(92, Math.max(18, Math.round(((stageIndex(deal.stage_id) + 1) / total) * 86)));
}

function openTasks(deal: Deal) {
  return crmStore.tasks.value.filter((task) => task.deal_id === deal.id && !task.done_at);
}

function move(deal: Deal, event: Event) {
  const stageId = (event.target as HTMLSelectElement).value;
  void crmStore.moveDeal(deal, stageId);
}
</script>

<template>
  <section class="stack">
    <form class="panel form-line" @submit.prevent="crmStore.createDeal">
      <label>Компания
        <select v-model="crmStore.dealForm.value.company_id" required>
          <option value="">Выбрать</option>
          <option v-for="company in crmStore.companies.value" :key="company.id" :value="company.id">{{ company.name }}</option>
        </select>
      </label>
      <label>Сделка<input v-model="crmStore.dealForm.value.title" /></label>
      <label>Сумма<input v-model.number="crmStore.dealForm.value.amount" type="number" /></label>
      <label>Лид
        <select v-model="crmStore.dealForm.value.lead_id">
          <option value="">Без лида</option>
          <option
            v-for="lead in crmStore.leads.value.filter((item) => item.company_id === crmStore.dealForm.value.company_id)"
            :key="lead.id"
            :value="lead.id"
          >{{ lead.title }}</option>
        </select>
      </label>
      <label>Этап
        <select v-model="crmStore.dealForm.value.stage_id" required>
          <option value="">Выбрать</option>
          <option v-for="stage in crmStore.allStages.value" :key="stage.id" :value="stage.id">{{ stage.name }}</option>
        </select>
      </label>
      <button type="submit">Создать</button>
    </form>

    <div class="mode-tabs">
      <button
        v-for="item in modes"
        :key="item.code"
        type="button"
        :class="{ active: mode === item.code }"
        @click="mode = item.code"
      >{{ item.label }}</button>
    </div>

    <div v-if="mode === 'kanban'" class="kanban">
      <section v-for="column in crmStore.dealsByStage.value" :key="column.stage.id" class="kanban-column">
        <header>
          <strong>{{ column.stage.name }}</strong>
          <small>{{ column.deals.length }} · {{ crmStore.money(column.amount) }}</small>
        </header>
        <article v-for="deal in column.deals" :key="deal.id" class="deal-card" @click="selectedDeal = deal">
          <header>
            <div>
              <strong>{{ deal.title }}</strong>
              <small>{{ companyName(deal.company_id) }}</small>
            </div>
            <span class="health-pill">{{ probability(deal) }}%</span>
          </header>
          <div class="deal-amount">{{ crmStore.money(deal.amount) }}</div>
          <div class="progress-line"><span :style="{ width: `${probability(deal)}%` }"></span></div>
          <dl class="deal-facts">
            <div><dt>Next Action</dt><dd>{{ openTasks(deal)[0]?.title ?? "Follow-up" }}</dd></div>
            <div><dt>Owner</dt><dd>Sales</dd></div>
            <div><dt>Tasks</dt><dd>{{ openTasks(deal).length }} open</dd></div>
          </dl>
          <select :value="deal.stage_id" @click.stop @change="move(deal, $event)">
            <option v-for="stage in crmStore.allStages.value" :key="stage.id" :value="stage.id">{{ stage.name }}</option>
          </select>
          <button class="secondary" type="button" @click.stop="crmStore.createNote('deal', deal.id)">Заметка</button>
        </article>
      </section>
    </div>

    <section v-else-if="mode === 'table'" class="panel">
      <table class="data-table">
        <thead><tr><th>Deal</th><th>Company</th><th>Stage</th><th>Amount</th><th>Status</th></tr></thead>
        <tbody>
          <tr v-for="deal in crmStore.deals.value" :key="deal.id" @click="selectedDeal = deal">
            <td>{{ deal.title }}</td>
            <td>{{ companyName(deal.company_id) }}</td>
            <td>{{ crmStore.allStages.value.find((stage) => stage.id === deal.stage_id)?.name ?? "Stage" }}</td>
            <td>{{ crmStore.money(deal.amount) }}</td>
            <td>{{ deal.status }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-else-if="mode === 'list'" class="panel">
      <article v-for="deal in crmStore.deals.value" :key="deal.id" class="entity-row" @click="selectedDeal = deal">
        <div>
          <strong>{{ deal.title }}</strong>
          <small>{{ companyName(deal.company_id) }} · {{ probability(deal) }}% probability</small>
        </div>
        <span>{{ crmStore.money(deal.amount) }}</span>
      </article>
    </section>

    <section v-else class="panel">
      <h2>Forecast</h2>
      <article v-for="row in forecast" :key="row.stage.id" class="list-row">
        <span>{{ row.stage.name }} · {{ row.probability }}%</span>
        <small>{{ crmStore.money(row.weighted) }}</small>
      </article>
    </section>

    <DealDrawer :deal="selectedDeal" @close="selectedDeal = null" />
  </section>
</template>
