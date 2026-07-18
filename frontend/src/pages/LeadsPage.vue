<script setup lang="ts">
import { onMounted, ref } from "vue";

import { crmStore } from "../stores/crm";

onMounted(() => {
  void crmStore.refreshAll();
});

const creationMode = ref<"lead" | "contact">("lead");

function companyName(companyId: string) {
  return crmStore.companies.value.find((company) => company.id === companyId)?.name ?? "Компания";
}
</script>

<template>
  <section class="stack">
    <section class="workspace-hero compact-hero leads-intro">
      <p>Новые обращения и контакты до создания сделки.</p>
      <RouterLink class="button-link secondary-link" to="/inbox">Открыть входящие</RouterLink>
    </section>

    <div class="mode-tabs leads-create-tabs" role="tablist" aria-label="Тип новой записи">
      <button type="button" role="tab" :aria-selected="creationMode === 'lead'" :class="{ active: creationMode === 'lead' }" @click="creationMode = 'lead'">Новый лид</button>
      <button type="button" role="tab" :aria-selected="creationMode === 'contact'" :class="{ active: creationMode === 'contact' }" @click="creationMode = 'contact'">Новый контакт</button>
    </div>

    <section class="section-grid">
    <form v-if="creationMode === 'contact'" class="panel wide" @submit.prevent="crmStore.createContact">
      <h2>Новый контакт</h2>
      <label>Компания в CRM
        <select v-model="crmStore.contactForm.value.company_id" required>
          <option value="">Выбрать</option>
          <option v-for="company in crmStore.companies.value" :key="company.id" :value="company.id">{{ company.name }}</option>
        </select>
      </label>
      <label>Имя<input v-model="crmStore.contactForm.value.name" required autocomplete="name" /></label>
      <label>Телефон<input v-model="crmStore.contactForm.value.phone" type="tel" autocomplete="tel" /></label>
      <label>Email<input v-model="crmStore.contactForm.value.email" type="email" autocomplete="email" /></label>
      <label>Новая компания, если её нет в списке<input v-model="crmStore.contactForm.value.company_name" placeholder="Название компании" /></label>
      <button type="submit">Создать контакт</button>
    </form>

    <form v-else class="panel wide" @submit.prevent="crmStore.createLead">
      <h2>Новый лид</h2>
      <label>Компания
        <select v-model="crmStore.leadForm.value.company_id" required>
          <option value="">Выбрать</option>
          <option v-for="company in crmStore.companies.value" :key="company.id" :value="company.id">{{ company.name }}</option>
        </select>
      </label>
      <label>Название<input v-model="crmStore.leadForm.value.title" required /></label>
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

<style scoped>
.leads-intro { min-height: 0; }
.leads-intro > p { margin: 0; color: var(--muted); }
.leads-create-tabs { width: fit-content; }
</style>
