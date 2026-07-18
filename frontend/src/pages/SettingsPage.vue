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
      <label>ID рабочего пространства<input v-model="crmStore.tenantId.value" @change="crmStore.saveTenantId" /></label>
      <p class="hint">{{ crmStore.activeTenant.value?.name }} / {{ crmStore.activeTenant.value?.slug }}</p>
    </section>

    <section class="section-grid">
      <form class="panel" @submit.prevent="crmStore.createConnectorAccount">
        <h2>Интеграции</h2>
        <label>Коннектор
          <select v-model="crmStore.connectorAccountForm.value.connector_code">
            <option v-for="definition in crmStore.connectorDefinitions.value" :key="definition.code" :value="definition.code">
              {{ definition.title }}
            </option>
          </select>
        </label>
        <label>Название<input v-model="crmStore.connectorAccountForm.value.title" /></label>
        <button type="submit">Подключить</button>
        <article v-for="account in crmStore.connectorAccounts.value" :key="account.id" class="list-row">
          <span>{{ account.title }}</span>
          <small>{{ account.status }} · {{ account.credentials_encrypted ? "данные защищены" : "без шифрования" }}</small>
          <button class="secondary" type="button" @click="crmStore.syncConnectorAccount(account.id)">Синхронизировать</button>
        </article>
        <article v-for="run in crmStore.connectorRuns.value.slice(0, 5)" :key="run.id" class="list-row">
          <span>{{ run.job_type }} / {{ run.status }}</span>
          <small>Создано: {{ run.created_count }} · попытка {{ run.attempt }}/{{ run.max_attempts }}</small>
          <button
            v-if="run.status === 'failed' || run.status === 'retry_scheduled'"
            class="secondary"
            type="button"
            @click="crmStore.retryConnectorRun(run.id)"
          >Повторить</button>
        </article>
      </form>

      <form class="panel" @submit.prevent="crmStore.applyCompanyTemplate">
        <h2>Шаблоны</h2>
        <label>Шаблон
          <select v-model="crmStore.templateApplyForm.value.template_code">
            <option v-for="template in crmStore.companyTemplates.value" :key="template.code" :value="template.code">
              {{ template.title }}
            </option>
          </select>
        </label>
        <label class="check-row"><input v-model="crmStore.templateApplyForm.value.include_pipeline" type="checkbox" /> Воронка</label>
        <label class="check-row"><input v-model="crmStore.templateApplyForm.value.include_knowledge" type="checkbox" /> База знаний</label>
        <button type="submit">Применить</button>
      </form>

      <form class="panel" @submit.prevent="crmStore.updateTenantPlan">
        <h2>Администрирование</h2>
        <label>Тариф<input v-model="crmStore.planForm.value.plan_code" /></label>
        <label>Лимит пользователей<input v-model.number="crmStore.planForm.value.users_limit" type="number" /></label>
        <label>Лимит AI-запросов<input v-model.number="crmStore.planForm.value.ai_requests_limit" type="number" /></label>
        <button type="submit">Сохранить тариф</button>
      </form>

      <section class="panel">
        <h2>Рабочая среда</h2>
        <article v-for="flag in crmStore.featureFlags.value" :key="flag.id" class="list-row">
          <span>{{ flag.title }}</span>
          <button class="secondary" type="button" @click="crmStore.toggleFeatureFlag(flag)">
            {{ flag.enabled ? "Включено" : "Выключено" }}
          </button>
        </article>
        <div class="button-row">
          <button class="secondary" type="button" @click="crmStore.createAuditMarker">Создать отметку аудита</button>
          <button class="secondary" type="button" @click="crmStore.exportTenantData">Экспортировать данные</button>
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
