<script setup lang="ts">
import { onMounted } from "vue";

import { crmStore } from "../stores/crm";

onMounted(() => {
  void crmStore.refreshAll();
});

function companyName(companyId: string) {
  return crmStore.companies.value.find((company) => company.id === companyId)?.name ?? "Компания";
}
</script>

<template>
  <section class="stack">
    <section class="workspace-hero compact-hero">
      <div>
        <p class="eyebrow">Demand Pipeline</p>
        <h1>Leads</h1>
        <p>Новые обращения, контакты и источники до создания сделки.</p>
      </div>
      <RouterLink class="button-link secondary-link" to="/inbox">Communication Hub</RouterLink>
    </section>

    <section class="section-grid">
    <form class="panel" @submit.prevent="crmStore.createContact">
      <h2>Новый контакт</h2>
      <label>Компания
        <select v-model="crmStore.contactForm.value.company_id" required>
          <option value="">Выбрать</option>
          <option v-for="company in crmStore.companies.value" :key="company.id" :value="company.id">{{ company.name }}</option>
        </select>
      </label>
      <label>Имя<input v-model="crmStore.contactForm.value.name" /></label>
      <label>Телефон<input v-model="crmStore.contactForm.value.phone" /></label>
      <label>Email<input v-model="crmStore.contactForm.value.email" /></label>
      <label>Компания<input v-model="crmStore.contactForm.value.company_name" /></label>
      <button type="submit">Создать контакт</button>
    </form>

    <form class="panel" @submit.prevent="crmStore.createLead">
      <h2>Новый лид</h2>
      <label>Компания
        <select v-model="crmStore.leadForm.value.company_id" required>
          <option value="">Выбрать</option>
          <option v-for="company in crmStore.companies.value" :key="company.id" :value="company.id">{{ company.name }}</option>
        </select>
      </label>
      <label>Название<input v-model="crmStore.leadForm.value.title" /></label>
      <label>Источник<input v-model="crmStore.leadForm.value.source" /></label>
      <label>Контакт
        <select v-model="crmStore.leadForm.value.contact_id">
          <option value="">Без контакта</option>
          <option
            v-for="contact in crmStore.contacts.value.filter((item) => item.company_id === crmStore.leadForm.value.company_id)"
            :key="contact.id"
            :value="contact.id"
          >{{ contact.name }}</option>
        </select>
      </label>
      <button type="submit">Создать лид</button>
    </form>

    <section class="panel wide">
      <h2>Лиды</h2>
      <div v-for="lead in crmStore.leads.value" :key="lead.id" class="entity-row">
        <div>
          <strong>{{ lead.title }}</strong>
          <small>{{ companyName(lead.company_id) }} · {{ lead.source ?? "Источник не указан" }} · {{ lead.status }}</small>
        </div>
        <button class="secondary" type="button" @click="crmStore.createNote('lead', lead.id)">Заметка</button>
      </div>
      <p v-if="!crmStore.leads.value.length" class="empty">Лидов пока нет</p>
    </section>
    </section>
  </section>
</template>
