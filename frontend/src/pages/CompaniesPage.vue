<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import CompanyDrawer from "../components/crm/CompanyDrawer.vue";
import { crmStore } from "../stores/crm";
import type { Company } from "../types";

const query = ref("");
const sort = ref<"health" | "name" | "pipeline">("health");
const selectedCompany = ref<Company | null>(null);

onMounted(() => {
  void crmStore.refreshAll();
});

function companyDeals(company: Company) {
  return crmStore.deals.value.filter((deal) => deal.company_id === company.id);
}

function companyTasks(company: Company) {
  return crmStore.tasks.value.filter((task) => task.company_id === company.id && !task.done_at);
}

function companyPipeline(company: Company) {
  return companyDeals(company).reduce((sum, deal) => sum + Number(deal.amount ?? 0), 0);
}

function companyHealth(company: Company) {
  return Math.min(98, 58 + companyDeals(company).length * 9 + companyTasks(company).length * 4);
}

function healthTone(company: Company) {
  const health = companyHealth(company);
  if (health >= 60) return "good";
  if (health >= 45) return "warn";
  return "bad";
}

function companyInitial(company: Company) {
  return company.name.trim().slice(0, 1).toUpperCase();
}

function nextAction(company: Company) {
  const task = companyTasks(company)[0];
  if (task) return task.title;
  if (!companyDeals(company).length) return "Создать первую сделку";
  return "Запланировать follow-up";
}

async function openCompany(company: Company) {
  selectedCompany.value = company;
  await crmStore.loadCompanyWorkspace(company.id);
  await crmStore.refreshCompanyCopilot(company.id);
}

const filteredCompanies = computed(() => {
  const needle = query.value.trim().toLowerCase();
  const rows = crmStore.companies.value.filter((company) => {
    if (!needle) return true;
    return [company.name, company.industry, company.website].some((value) => String(value ?? "").toLowerCase().includes(needle));
  });
  return rows.sort((left, right) => {
    if (sort.value === "name") return left.name.localeCompare(right.name);
    if (sort.value === "pipeline") return companyPipeline(right) - companyPipeline(left);
    return companyHealth(right) - companyHealth(left);
  });
});

const totalPipeline = computed(() => filteredCompanies.value.reduce((sum, company) => sum + companyPipeline(company), 0));
const totalDeals = computed(() => filteredCompanies.value.reduce((sum, company) => sum + companyDeals(company).length, 0));
const averageHealth = computed(() => {
  if (!filteredCompanies.value.length) return 0;
  const sum = filteredCompanies.value.reduce((acc, company) => acc + companyHealth(company), 0);
  return Math.round(sum / filteredCompanies.value.length);
});
</script>

<template>
  <section class="companies-workspace">
    <header class="companies-head">
      <div>
        <h1>Companies</h1>
        <p>{{ crmStore.companies.value.length }} компаний</p>
      </div>
    </header>

    <section class="companies-controls">
      <label class="companies-search">
        <span>⌕</span>
        <input v-model="query" placeholder="Поиск компаний..." />
      </label>
      <label class="companies-filter">
        <span>▿</span>
        <select v-model="sort">
          <option value="health">Фильтры</option>
          <option value="pipeline">Pipeline</option>
          <option value="name">Name</option>
        </select>
      </label>
      <button type="button" class="new-company-button">+ New Company</button>
    </section>

    <section class="companies-metrics">
      <article class="company-metric-card">
        <div><span>Deals</span><strong>{{ totalDeals }}</strong><small>Открытых сделок</small></div>
        <span class="metric-orb blue">□</span>
      </article>
      <article class="company-metric-card">
        <div><span>Pipeline</span><strong>{{ crmStore.money(totalPipeline) }}</strong><small>Сумма пайплайна</small></div>
        <span class="metric-orb green">⌘</span>
      </article>
      <article class="company-metric-card">
        <div><span>Avg. Health</span><strong>{{ averageHealth }}</strong><small>Средний Health</small></div>
        <span class="metric-orb purple">♡</span>
      </article>
    </section>

    <section class="companies-list">
      <article
        v-for="company in filteredCompanies"
        :key="company.id"
        class="company-list-row clickable-row"
        :class="{ selected: selectedCompany?.id === company.id }"
        @click="openCompany(company)"
      >
        <span class="company-avatar" :class="healthTone(company)">{{ companyInitial(company) }}</span>
        <div class="company-main">
          <strong>{{ company.name }}</strong>
          <small>B2B · {{ company.website?.replace("https://", "") ?? "example.com" }}</small>
        </div>
        <div class="health-cell">
          <span>Health {{ companyHealth(company) }}</span>
          <div class="company-health-line" :class="healthTone(company)">
            <span :style="{ width: `${companyHealth(company)}%` }"></span>
          </div>
        </div>
        <div class="row-stat"><strong>{{ companyDeals(company).length }}</strong><small>Deals</small></div>
        <div class="row-stat"><strong>{{ companyTasks(company).length }}</strong><small>Tasks</small></div>
        <div class="next-cell">
          <small>Next Action</small>
          <span>{{ nextAction(company) }}</span>
        </div>
      </article>

      <p v-if="!filteredCompanies.length" class="empty">Компаний не найдено</p>
    </section>

    <details class="panel create-drawer companies-create">
      <summary>New Company</summary>
      <form class="compact-form" @submit.prevent="crmStore.createCompany">
        <label>Название<input v-model="crmStore.companyForm.value.name" /></label>
        <label>Сайт<input v-model="crmStore.companyForm.value.website" /></label>
        <label>Отрасль<input v-model="crmStore.companyForm.value.industry" /></label>
        <label>Описание<textarea v-model="crmStore.companyForm.value.description"></textarea></label>
        <button type="submit">Создать</button>
      </form>
    </details>

    <CompanyDrawer :company="selectedCompany" @close="selectedCompany = null" />
  </section>
</template>
