<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import UiAlert from "../components/ui/UiAlert.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiIcon from "../components/ui/UiIcon.vue";
import { statusLabel } from "../design-system/statusDictionary";
import { crmStore } from "../stores/crm";

type SettingsSection = "workspace" | "integrations" | "templates" | "admin";
const activeSection = ref<SettingsSection>("workspace");
const loading = ref(true);
const canAdmin = computed(() => ["owner", "admin"].includes(crmStore.me.value?.role ?? ""));

onMounted(async () => {
  try {
    await Promise.allSettled([
      crmStore.refreshMe(),
      crmStore.refreshConnectors(),
      crmStore.refreshTemplates(),
      crmStore.refreshProduction()
    ]);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="settings-page">
    <header class="settings-hero"><div><p class="eyebrow">Рабочее пространство</p><h2>Настройки</h2><p>Управление компанией, интеграциями, шаблонами и доступными возможностями.</p></div><UiButton variant="secondary" icon="refresh" :loading="loading" @click="crmStore.refreshProduction">Обновить</UiButton></header>
    <nav class="settings-nav" aria-label="Разделы настроек">
      <button v-for="item in [{id:'workspace',label:'Компания',icon:'companies'},{id:'integrations',label:'Интеграции',icon:'automation'},{id:'templates',label:'Шаблоны',icon:'file'},{id:'admin',label:'Администрирование',icon:'settings'}]" :key="item.id" type="button" :class="{ active: activeSection === item.id }" @click="activeSection = item.id as SettingsSection"><UiIcon :name="item.icon as any" :size="18" />{{ item.label }}</button>
    </nav>
    <div v-if="loading" class="settings-loading"><span></span><span></span></div>

    <section v-show="!loading && activeSection === 'workspace'" class="settings-grid">
    <section class="panel settings-card">
      <header><UiIcon name="companies" :size="20" /><div><h2>Компания</h2><p>Идентификатор активного рабочего пространства.</p></div></header>
      <label>ID рабочего пространства<input v-model="crmStore.tenantId.value" @change="crmStore.saveTenantId" /></label>
      <p class="hint">{{ crmStore.activeTenant.value?.name }} / {{ crmStore.activeTenant.value?.slug }}</p>
    </section>

    <section class="panel settings-card">
      <header><UiIcon name="file" :size="20" /><div><h2>Заметка по умолчанию</h2><p>Используется быстрыми действиями в лидах и сделках.</p></div></header>
      <label>Текст<textarea v-model="crmStore.noteForm.value.text"></textarea></label>
    </section>
    <section class="panel settings-card wide">
      <header><UiIcon name="archive" :size="20" /><div><h2>История заметок</h2><p>Последние сохранённые записи.</p></div></header>
      <div v-for="note in crmStore.notes.value" :key="note.id" class="list-row"><span>{{ note.text }}</span><small>{{ note.lead_id ? "Лид" : "Сделка" }}</small></div>
      <p v-if="!crmStore.notes.value.length" class="empty">Заметок пока нет</p>
    </section>
    </section>

    <section v-show="!loading && activeSection === 'integrations'" class="settings-grid">
      <form class="panel settings-card wide" @submit.prevent="crmStore.createConnectorAccount">
        <header><UiIcon name="automation" :size="20" /><div><h2>Интеграции</h2><p>Источники писем, звонков и календарных событий.</p></div></header>
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
          <small>{{ statusLabel(account.status, "connector") }} · {{ account.credentials_encrypted ? "данные защищены" : "без шифрования" }}</small>
          <button class="secondary" type="button" @click="crmStore.syncConnectorAccount(account.id)">Синхронизировать</button>
        </article>
        <article v-for="run in crmStore.connectorRuns.value.slice(0, 5)" :key="run.id" class="list-row">
          <span>{{ run.job_type }} / {{ statusLabel(run.status, "connector") }}</span>
          <small>Создано: {{ run.created_count }} · попытка {{ run.attempt }}/{{ run.max_attempts }}</small>
          <button
            v-if="run.status === 'failed' || run.status === 'retry_scheduled'"
            class="secondary"
            type="button"
            @click="crmStore.retryConnectorRun(run.id)"
          >Повторить</button>
        </article>
      </form>
    </section>

    <section v-show="!loading && activeSection === 'templates'" class="settings-grid">
      <form class="panel settings-card wide" @submit.prevent="crmStore.applyCompanyTemplate">
        <header><UiIcon name="file" :size="20" /><div><h2>Шаблоны компании</h2><p>Быстрый старт структуры продаж и базы знаний.</p></div></header>
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
    </section>

    <section v-show="!loading && activeSection === 'admin'" class="settings-grid">
      <UiAlert v-if="!canAdmin" tone="warning" title="Недостаточно прав">Тариф, feature flags, аудит и экспорт доступны владельцу или администратору.</UiAlert>
      <form v-if="canAdmin" class="panel settings-card" @submit.prevent="crmStore.updateTenantPlan">
        <header><UiIcon name="settings" :size="20" /><div><h2>Тариф и лимиты</h2><p>Ограничения рабочего пространства.</p></div></header>
        <label>Тариф<input v-model="crmStore.planForm.value.plan_code" /></label>
        <label>Лимит пользователей<input v-model.number="crmStore.planForm.value.users_limit" type="number" /></label>
        <label>Лимит AI-запросов<input v-model.number="crmStore.planForm.value.ai_requests_limit" type="number" /></label>
        <button type="submit">Сохранить тариф</button>
      </form>

      <section v-if="canAdmin" class="panel settings-card">
        <header><UiIcon name="sparkles" :size="20" /><div><h2>Рабочая среда</h2><p>Feature flags и операции с данными.</p></div></header>
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
  </section>
</template>

<style scoped>
.settings-page{display:grid;gap:16px}.settings-hero{display:flex;align-items:flex-end;justify-content:space-between;gap:20px}.settings-hero h2{margin:4px 0 6px;font-size:28px}.settings-hero p:last-child{margin:0;color:var(--color-text-muted)}.settings-nav{display:flex;gap:4px;overflow:auto;border:1px solid var(--color-border);border-radius:var(--radius-card);padding:4px;background:var(--color-surface)}.settings-nav button{gap:7px;min-height:38px;color:var(--color-text-muted);background:transparent;box-shadow:none;white-space:nowrap}.settings-nav button.active{color:var(--color-primary);background:var(--color-primary-soft)}.settings-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;align-items:start}.settings-grid>.wide,.settings-grid>:deep(.ui-alert){grid-column:1/-1}.settings-card{display:grid;gap:14px;border-radius:var(--radius-panel);padding:20px}.settings-card>header{display:flex;align-items:flex-start;gap:10px}.settings-card>header>svg{color:var(--color-primary)}.settings-card h2{margin:0 0 3px}.settings-card header p{margin:0;color:var(--color-text-muted);font-size:var(--font-size-meta)}.settings-loading{display:grid;grid-template-columns:1fr 1fr;gap:14px}.settings-loading span{height:260px;border-radius:var(--radius-panel);background:linear-gradient(90deg,var(--color-surface),var(--color-surface-muted),var(--color-surface));background-size:200% 100%;animation:settings-pulse 1.2s infinite}@keyframes settings-pulse{to{background-position:-200% 0}}
@media(max-width:720px){.settings-hero{align-items:flex-start;flex-direction:column}.settings-grid,.settings-loading{grid-template-columns:1fr}.settings-grid>*{grid-column:1!important}.settings-nav{margin-inline:-14px;border-radius:0;border-inline:0}}
</style>
