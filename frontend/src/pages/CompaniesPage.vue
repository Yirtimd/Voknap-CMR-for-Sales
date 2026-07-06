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

function nextAction(company: Company) {
  const task = companyTasks(company)[0];
  if (task) return task.title;
  if (!companyDeals(company).length) return "Создать первую сделку";
  return "Запланировать follow-up";
}

async function openCompany(company: Company) {
  selectedCompany.value = company;
  await crmStore.loadCompanyWorkspace(company.id);
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
</script>

<template>
  <section class="stack">
    <section class="workspace-hero compact-hero">
      <div>
        <p class="eyebrow">Company Workspace</p>
        <h1>Работаю с клиентами</h1>
        <p>Найди компанию, посмотри состояние, next action и открой рабочее пространство клиента.</p>
      </div>
      <RouterLink class="button-link secondary-link" to="/tasks">Все задачи</RouterLink>
    </section>

    <section class="panel wide">
      <div class="toolbar">
        <label class="search-field">Search
          <input v-model="query" placeholder="Компания, отрасль, сайт" />
        </label>
        <label>Sort
          <select v-model="sort">
            <option value="health">Health</option>
            <option value="pipeline">Pipeline</option>
            <option value="name">Name</option>
          </select>
        </label>
      </div>

      <article
        v-for="company in filteredCompanies"
        :key="company.id"
        class="company-work-row clickable-row"
        @click="openCompany(company)"
      >
        <div class="company-main">
          <strong>{{ company.name }}</strong>
          <small>{{ company.industry ?? "Отрасль не указана" }} · {{ company.website ?? "site not set" }}</small>
        </div>
        <div class="health-cell">
          <span>Health {{ companyHealth(company) }}</span>
          <meter min="0" max="100" :value="companyHealth(company)"></meter>
        </div>
        <div class="row-stat"><strong>{{ companyDeals(company).length }}</strong><small>Deals</small></div>
        <div class="row-stat"><strong>{{ companyTasks(company).length }}</strong><small>Tasks</small></div>
        <div class="next-cell">
          <small>Next Action</small>
          <span>{{ nextAction(company) }}</span>
        </div>
        <button class="secondary" type="button" @click.stop="openCompany(company)">Open</button>
      </article>

      <p v-if="!filteredCompanies.length" class="empty">Компаний не найдено</p>
    </section>

    <details class="panel create-drawer">
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
