<script setup lang="ts">
import { onMounted } from "vue";

import { crmStore } from "../stores/crm";

onMounted(async () => {
  await Promise.allSettled([
    crmStore.refreshConnectors(),
    crmStore.refreshTemplates(),
    crmStore.refreshProduction()
  ]);
});
</script>

<template>
  <section class="stack">
    <section class="panel">
      <h2>Компания</h2>
      <label>Tenant ID<input v-model="crmStore.tenantId.value" @change="crmStore.saveTenantId" /></label>
      <p class="hint">{{ crmStore.activeTenant.value?.name }} / {{ crmStore.activeTenant.value?.slug }}</p>
    </section>

    <section class="section-grid">
      <form class="panel" @submit.prevent="crmStore.createConnectorAccount">
        <h2>Integrations</h2>
        <label>Connector
          <select v-model="crmStore.connectorAccountForm.value.connector_code">
            <option v-for="definition in crmStore.connectorDefinitions.value" :key="definition.code" :value="definition.code">
              {{ definition.title }}
            </option>
          </select>
        </label>
        <label>Title<input v-model="crmStore.connectorAccountForm.value.title" /></label>
        <button type="submit">Подключить</button>
        <article v-for="account in crmStore.connectorAccounts.value" :key="account.id" class="list-row">
          <span>{{ account.title }}</span>
          <small>{{ account.status }}</small>
        </article>
      </form>

      <form class="panel" @submit.prevent="crmStore.applyCompanyTemplate">
        <h2>Templates</h2>
        <label>Template
          <select v-model="crmStore.templateApplyForm.value.template_code">
            <option v-for="template in crmStore.companyTemplates.value" :key="template.code" :value="template.code">
              {{ template.title }}
            </option>
          </select>
        </label>
        <label class="check-row"><input v-model="crmStore.templateApplyForm.value.include_pipeline" type="checkbox" /> Pipeline</label>
        <label class="check-row"><input v-model="crmStore.templateApplyForm.value.include_knowledge" type="checkbox" /> Knowledge</label>
        <button type="submit">Применить</button>
      </form>

      <form class="panel" @submit.prevent="crmStore.updateTenantPlan">
        <h2>Administration</h2>
        <label>Plan<input v-model="crmStore.planForm.value.plan_code" /></label>
        <label>Users<input v-model.number="crmStore.planForm.value.users_limit" type="number" /></label>
        <label>AI requests<input v-model.number="crmStore.planForm.value.ai_requests_limit" type="number" /></label>
        <button type="submit">Сохранить тариф</button>
      </form>

      <section class="panel">
        <h2>Production</h2>
        <article v-for="flag in crmStore.featureFlags.value" :key="flag.id" class="list-row">
          <span>{{ flag.title }}</span>
          <button class="secondary" type="button" @click="crmStore.toggleFeatureFlag(flag)">
            {{ flag.enabled ? "On" : "Off" }}
          </button>
        </article>
        <div class="button-row">
          <button class="secondary" type="button" @click="crmStore.createAuditMarker">Audit marker</button>
          <button class="secondary" type="button" @click="crmStore.exportTenantData">Export tenant</button>
        </div>
      </section>
    </section>

    <section class="panel wide">
      <h2>Заметка по умолчанию</h2>
      <label>Текст<textarea v-model="crmStore.noteForm.value.text"></textarea></label>
      <p class="hint">Эта заметка добавляется кнопками в лидах и сделках.</p>
    </section>

    <section class="panel wide">
      <h2>История заметок</h2>
      <div v-for="note in crmStore.notes.value" :key="note.id" class="list-row">
        <span>{{ note.text }}</span>
        <small>{{ note.lead_id ? "Лид" : "Сделка" }}</small>
      </div>
      <p v-if="!crmStore.notes.value.length" class="empty">Заметок пока нет</p>
    </section>
  </section>
</template>
