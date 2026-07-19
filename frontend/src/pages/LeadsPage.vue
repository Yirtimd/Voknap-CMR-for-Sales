<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import EntityCrudDrawer from "../components/crm/EntityCrudDrawer.vue";
import { crmStore } from "../stores/crm";
import type { Contact, EntityType, Lead, Note } from "../types";

const route = useRoute();
const router = useRouter();

onMounted(async () => {
  await crmStore.refreshAll();
  openFromRoute();
});

const crudType = ref<EntityType | null>(null);
const crudRecord = ref<Contact | Lead | Note | null>(null);
const crudMode = ref<"view" | "edit" | "create">("view");
const crudInitialValues = ref<Record<string, unknown>>({});

function openCrud(type: "contacts" | "leads" | "notes", record: Contact | Lead | Note | null = null, mode: "view" | "edit" | "create" = record ? "view" : "create", initialValues: Record<string, unknown> = {}) {
  crudType.value = type;
  crudRecord.value = record;
  crudMode.value = mode;
  crudInitialValues.value = initialValues;
}

function openFromRoute() {
  const leadId = typeof route.query.record === "string" ? route.query.record : "";
  const contactId = typeof route.query.contact === "string" ? route.query.contact : "";
  const lead = crmStore.leads.value.find((item) => item.id === leadId);
  const contact = crmStore.contacts.value.find((item) => item.id === contactId);
  if (lead) openCrud("leads", lead);
  else if (contact) openCrud("contacts", contact);
}

function closeCrud() {
  crudType.value = null;
  crudRecord.value = null;
  crudInitialValues.value = {};
  if (route.query.record || route.query.contact) void router.replace({ query: { ...route.query, record: undefined, contact: undefined } });
}

watch(() => [route.query.record, route.query.contact], openFromRoute);

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

    <div class="mode-tabs leads-create-tabs" aria-label="Создание записей">
      <button type="button" class="active" @click="openCrud('leads')">＋ Новый лид</button>
      <button type="button" @click="openCrud('contacts')">＋ Новый контакт</button>
    </div>

    <section class="section-grid">
    <section class="panel wide">
      <h2>Лиды</h2>
      <div v-for="lead in crmStore.leads.value" :key="lead.id" class="entity-row" @click="openCrud('leads', lead)">
        <div>
          <strong>{{ lead.title }}</strong>
          <small>{{ companyName(lead.company_id) }} · {{ lead.source ?? "Источник не указан" }} · {{ lead.status }}</small>
        </div>
        <div class="button-row" @click.stop><button class="secondary" type="button" @click="openCrud('leads', lead, 'edit')">Редактировать</button><button class="secondary" type="button" @click="openCrud('notes', null, 'create', { company_id: lead.company_id, lead_id: lead.id })">Заметка</button></div>
      </div>
      <p v-if="!crmStore.leads.value.length" class="empty">Лидов пока нет</p>
    </section>

    <section class="panel wide">
      <div class="panel-head"><div><h2>Контакты</h2><p class="hint">Карточки контактных лиц и полный CRUD.</p></div><button type="button" @click="openCrud('contacts')">＋ Контакт</button></div>
      <div v-for="contact in crmStore.contacts.value" :key="contact.id" class="entity-row" @click="openCrud('contacts', contact)"><div><strong>{{ contact.name }}</strong><small>{{ contact.company_name || companyName(contact.company_id) }} · {{ contact.email || contact.phone || 'Нет контактов' }}</small></div><button class="secondary" type="button" @click.stop="openCrud('contacts', contact, 'edit')">Редактировать</button></div>
      <p v-if="!crmStore.contacts.value.length" class="empty">Контактов пока нет</p>
    </section>
    </section>

    <EntityCrudDrawer v-if="crudType" :entity-type="crudType" :record="crudRecord" :initial-mode="crudMode" :initial-values="crudInitialValues" @close="closeCrud" />
  </section>
</template>

<style scoped>
.leads-intro { min-height: 0; }
.leads-intro > p { margin: 0; color: var(--muted); }
.leads-create-tabs { width: fit-content; }
</style>
