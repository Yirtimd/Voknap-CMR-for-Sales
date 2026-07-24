<script setup lang="ts">
import { computed } from "vue";

import UiAlert from "../ui/UiAlert.vue";
import UiBadge from "../ui/UiBadge.vue";
import UiButton from "../ui/UiButton.vue";
import UiCard from "../ui/UiCard.vue";
import UiIcon from "../ui/UiIcon.vue";
import { statusLabel } from "../../design-system/statusDictionary";
import { crmStore } from "../../stores/crm";

const accountConnectorCodes = new Set(["email", "google_calendar", "microsoft_calendar"]);
const accountDefinitions = computed(() =>
  crmStore.connectorDefinitions.value.filter((item) => accountConnectorCodes.has(item.code))
);
const unavailableDefinitions = computed(() =>
  crmStore.connectorDefinitions.value.filter((item) => item.status === "requires_provider")
);
const emailAccounts = computed(() =>
  crmStore.connectorAccounts.value.filter((item) => item.connector_code === "email" && item.status === "connected")
);
const calendarAccounts = computed(() =>
  crmStore.connectorAccounts.value.filter(
    (item) => ["google_calendar", "microsoft_calendar"].includes(item.connector_code) && item.status === "connected"
  )
);

function applyEmailProvider() {
  const provider = crmStore.connectorAccountForm.value.email_provider;
  if (provider === "gmail") {
    Object.assign(crmStore.connectorAccountForm.value, {
      host: "imap.gmail.com",
      port: 993,
      smtp_host: "smtp.gmail.com",
      smtp_port: 465,
      use_ssl: true,
      smtp_use_ssl: true
    });
  }
}

function selectImportFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file) void crmStore.previewIntegrationImport(file);
}
</script>

<template>
  <section class="integration-stack">
    <UiAlert tone="info" title="Реальные подключения">
      Секреты шифруются. Синхронизации и отправки выполняет background worker с retry,
      idempotency и dead-letter queue.
    </UiAlert>

    <section class="integration-grid">
      <UiCard v-for="definition in crmStore.connectorDefinitions.value.filter((item) => item.status === 'ready')" :key="definition.code" class="capability-card">
        <header><UiIcon name="automation" :size="18" /><strong>{{ definition.title }}</strong><UiBadge tone="success">Доступно</UiBadge></header>
        <p>{{ definition.description }}</p>
      </UiCard>
    </section>

    <form class="panel settings-card wide" @submit.prevent="crmStore.createConnectorAccount">
      <header><UiIcon name="automation" :size="20" /><div><h2>Подключить аккаунт</h2><p>Email или календарь. OAuth-токены сохраняются только на сервере.</p></div></header>
      <label>Тип
        <select v-model="crmStore.connectorAccountForm.value.connector_code">
          <option v-for="definition in accountDefinitions" :key="definition.code" :value="definition.code">{{ definition.title }}</option>
        </select>
      </label>
      <label>Название<input v-model="crmStore.connectorAccountForm.value.title" required minlength="2" /></label>
      <template v-if="crmStore.connectorAccountForm.value.connector_code === 'email'">
        <div class="form-grid">
          <label>Провайдер
            <select v-model="crmStore.connectorAccountForm.value.email_provider" @change="applyEmailProvider">
              <option value="gmail">Gmail / Google Workspace</option>
              <option value="custom">Другой IMAP/SMTP</option>
            </select>
          </label>
          <label>Email / login<input v-model="crmStore.connectorAccountForm.value.username" type="email" required /></label>
          <label>App password<input v-model="crmStore.connectorAccountForm.value.password" type="password" required autocomplete="new-password" /></label>
          <label>From email<input v-model="crmStore.connectorAccountForm.value.from_email" type="email" placeholder="По умолчанию login" /></label>
          <label>IMAP host<input v-model="crmStore.connectorAccountForm.value.host" required /></label>
          <label>IMAP port<input v-model.number="crmStore.connectorAccountForm.value.port" type="number" min="1" max="65535" required /></label>
          <label>SMTP host<input v-model="crmStore.connectorAccountForm.value.smtp_host" required /></label>
          <label>SMTP port<input v-model.number="crmStore.connectorAccountForm.value.smtp_port" type="number" min="1" max="65535" required /></label>
          <label>Папка<input v-model="crmStore.connectorAccountForm.value.folder" required /></label>
          <label class="check-row"><input v-model="crmStore.connectorAccountForm.value.use_ssl" type="checkbox" /> IMAP SSL/TLS</label>
          <label class="check-row"><input v-model="crmStore.connectorAccountForm.value.smtp_use_ssl" type="checkbox" /> SMTP SSL/TLS</label>
        </div>
        <small class="hint">При подключении CRM реально проверяет IMAP и SMTP. Для Gmail нужен App Password. Microsoft 365 рекомендуется подключать через OAuth — basic auth может быть запрещён политикой tenant.</small>
      </template>
      <UiButton type="submit" :loading="crmStore.isLoading.value">Создать подключение</UiButton>
    </form>

    <section class="panel settings-card wide">
      <header><UiIcon name="externalLink" :size="20" /><div><h2>Аккаунты</h2><p>OAuth-подключение, ручной sync и безопасное отключение.</p></div></header>
      <article v-for="account in crmStore.connectorAccounts.value" :key="account.id" class="integration-row">
        <div><strong>{{ account.title }}</strong><small>{{ account.connector_code }} · {{ statusLabel(account.status, "connector") }}<template v-if="account.last_sync_at"> · {{ new Date(account.last_sync_at).toLocaleString() }}</template></small></div>
        <div class="button-row">
          <UiButton v-if="account.status === 'awaiting_authorization'" variant="primary" @click="crmStore.startConnectorOAuth(account.id)">Авторизовать OAuth</UiButton>
          <UiButton v-if="account.status === 'connected' && account.connector_code !== 'csv'" variant="secondary" @click="crmStore.syncConnectorAccount(account.id)">Sync</UiButton>
          <UiButton variant="ghost" @click="crmStore.disconnectConnectorAccount(account.id)">Отключить</UiButton>
        </div>
      </article>
      <p v-if="!crmStore.connectorAccounts.value.length" class="empty">Аккаунтов пока нет</p>
    </section>

    <form v-if="emailAccounts.length" class="panel settings-card" @submit.prevent="crmStore.sendIntegrationEmail">
      <header><UiIcon name="mail" :size="20" /><div><h2>Отправить email</h2><p>SMTP-отправка через очередь.</p></div></header>
      <label>Аккаунт<select v-model="crmStore.emailSendForm.value.account_id" required><option value="">Выбрать</option><option v-for="account in emailAccounts" :key="account.id" :value="account.id">{{ account.title }}</option></select></label>
      <label>Получатель<input v-model="crmStore.emailSendForm.value.recipient" type="email" required /></label>
      <label>Тема<input v-model="crmStore.emailSendForm.value.subject" required /></label>
      <label>Текст<textarea v-model="crmStore.emailSendForm.value.body" required></textarea></label>
      <UiButton type="submit">Добавить в очередь</UiButton>
    </form>

    <form v-if="calendarAccounts.length" class="panel settings-card" @submit.prevent="crmStore.createIntegrationCalendarEvent">
      <header><UiIcon name="calendar" :size="20" /><div><h2>Создать встречу</h2><p>Запись напрямую в Google/Microsoft Calendar.</p></div></header>
      <label>Календарь<select v-model="crmStore.calendarEventForm.value.account_id" required><option value="">Выбрать</option><option v-for="account in calendarAccounts" :key="account.id" :value="account.id">{{ account.title }}</option></select></label>
      <label>Название<input v-model="crmStore.calendarEventForm.value.title" required /></label>
      <div class="form-grid"><label>Начало<input v-model="crmStore.calendarEventForm.value.starts_at" type="datetime-local" required /></label><label>Окончание<input v-model="crmStore.calendarEventForm.value.ends_at" type="datetime-local" required /></label></div>
      <label>Участники<input v-model="crmStore.calendarEventForm.value.attendees" placeholder="one@example.com, two@example.com" /></label>
      <label>Описание<textarea v-model="crmStore.calendarEventForm.value.description"></textarea></label>
      <UiButton type="submit">Добавить в очередь</UiButton>
    </form>

    <section class="panel settings-card wide">
      <header><UiIcon name="arrowUp" :size="20" /><div><h2>CSV/XLSX import</h2><p>Preview, mapping и асинхронный импорт до 10 000 строк.</p></div></header>
      <label>Файл<input type="file" accept=".csv,.xlsx,.xlsm" @change="selectImportFile" /></label>
      <template v-if="crmStore.importPreview.value">
        <p class="hint">{{ crmStore.importPreview.value.filename }} · {{ crmStore.importPreview.value.total_rows }} строк</p>
        <div class="mapping-grid">
          <label v-for="header in crmStore.importPreview.value.headers" :key="header">{{ header }}
            <select v-model="crmStore.importMapping.value[header]">
              <option value="">Не импортировать</option>
              <option value="name">Имя</option><option value="phone">Телефон</option><option value="email">Email</option>
              <option value="company_name">Компания</option><option value="lead_title">Название лида</option><option value="source">Источник</option>
            </select>
          </label>
        </div>
        <div class="preview-table"><table><thead><tr><th v-for="header in crmStore.importPreview.value.headers" :key="header">{{ header }}</th></tr></thead><tbody><tr v-for="(row, index) in crmStore.importPreview.value.rows.slice(0, 5)" :key="index"><td v-for="header in crmStore.importPreview.value.headers" :key="header">{{ row[header] }}</td></tr></tbody></table></div>
        <UiButton @click="crmStore.enqueueIntegrationImport">Импортировать в фоне</UiButton>
      </template>
    </section>

    <form class="panel settings-card" @submit.prevent="crmStore.createWebhookEndpoint">
      <header><UiIcon name="externalLink" :size="20" /><div><h2>Webhook</h2><p>HTTPS + HMAC-SHA256.</p></div></header>
      <label>Название<input v-model="crmStore.webhookForm.value.title" required /></label>
      <label>HTTPS URL<input v-model="crmStore.webhookForm.value.url" type="url" required /></label>
      <label class="check-row"><input v-model="crmStore.webhookForm.value.event_types" type="checkbox" value="lead.created" /> lead.created</label>
      <UiButton type="submit">Создать webhook</UiButton>
      <UiAlert v-if="crmStore.revealedWebhookSecret.value" tone="warning" title="Секрет показывается один раз"><code>{{ crmStore.revealedWebhookSecret.value }}</code></UiAlert>
      <article v-for="endpoint in crmStore.webhookEndpoints.value" :key="endpoint.id" class="integration-row"><div><strong>{{ endpoint.title }}</strong><small>{{ endpoint.url }} · {{ endpoint.event_types.join(", ") }}</small></div><div class="button-row"><UiButton variant="secondary" @click="crmStore.testWebhookEndpoint(endpoint.id)">Тест</UiButton><UiButton variant="ghost" @click="crmStore.disableWebhookEndpoint(endpoint.id)">Отключить</UiButton></div></article>
    </form>

    <form class="panel settings-card" @submit.prevent="crmStore.issuePublicApiKey">
      <header><UiIcon name="settings" :size="20" /><div><h2>Public API</h2><p>Ключи хранятся только в виде SHA-256 hash.</p></div></header>
      <label>Название<input v-model="crmStore.apiKeyForm.value.title" required /></label>
      <label class="check-row"><input v-model="crmStore.apiKeyForm.value.scopes" type="checkbox" value="leads:read" /> leads:read</label>
      <label class="check-row"><input v-model="crmStore.apiKeyForm.value.scopes" type="checkbox" value="leads:write" /> leads:write</label>
      <UiButton type="submit">Создать API-ключ</UiButton>
      <UiAlert v-if="crmStore.revealedApiKey.value" tone="warning" title="Ключ показывается один раз"><code>{{ crmStore.revealedApiKey.value }}</code></UiAlert>
      <article v-for="key in crmStore.publicApiKeys.value" :key="key.id" class="integration-row"><div><strong>{{ key.title }}</strong><small>{{ key.key_prefix }}… · {{ key.scopes.join(", ") }} · {{ key.is_active ? "активен" : "отозван" }}</small></div><UiButton v-if="key.is_active" variant="ghost" @click="crmStore.revokePublicApiKey(key.id)">Отозвать</UiButton></article>
      <p class="hint">Endpoint: <code>/public/v1/leads</code>. Передавайте ключ в <code>X-API-Key</code>.</p>
    </form>

    <section class="panel settings-card wide">
      <header><UiIcon name="clock" :size="20" /><div><h2>Background jobs / DLQ</h2><p>Retry выполняется автоматически; dead jobs можно вернуть вручную.</p></div></header>
      <article v-for="job in crmStore.integrationJobs.value" :key="job.id" class="integration-row">
        <div><strong>{{ job.job_type }}</strong><small>{{ statusLabel(job.status, "connector") }} · попытка {{ job.attempt }}/{{ job.max_attempts }}<template v-if="job.last_error"> · {{ job.last_error }}</template></small></div>
        <UiButton v-if="job.status === 'dead'" variant="secondary" @click="crmStore.replayIntegrationJob(job.id)">Replay</UiButton>
      </article>
      <p v-if="!crmStore.integrationJobs.value.length" class="empty">Заданий пока нет</p>
    </section>

    <section class="panel settings-card wide">
      <header><UiIcon name="info" :size="20" /><div><h2>Нужен выбор провайдера</h2><p>Здесь нет фальшивых кнопок подключения.</p></div></header>
      <article v-for="definition in unavailableDefinitions" :key="definition.code" class="integration-row unavailable">
        <div><strong>{{ definition.title }}</strong><small>{{ definition.description }}</small><p>{{ definition.reason }}</p></div>
        <UiBadge tone="warning">Решение требуется</UiBadge>
      </article>
    </section>
  </section>
</template>

<style scoped>
.integration-stack{display:grid;gap:14px}.integration-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.capability-card{display:grid;gap:8px;padding:14px}.capability-card header{display:flex;align-items:center;gap:7px}.capability-card header :last-child{margin-left:auto}.capability-card p,.integration-row p{margin:0;color:var(--color-text-muted);font-size:var(--font-size-meta)}.form-grid,.mapping-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.mapping-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.integration-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 0;border-top:1px solid var(--color-border)}.integration-row>div:first-child{display:grid;gap:3px;min-width:0}.integration-row small{color:var(--color-text-muted);overflow-wrap:anywhere}.button-row{display:flex;gap:6px;flex-wrap:wrap}.preview-table{overflow:auto;border:1px solid var(--color-border);border-radius:var(--radius-control)}.preview-table table{width:100%;border-collapse:collapse}.preview-table th,.preview-table td{padding:8px;border-bottom:1px solid var(--color-border);text-align:left;white-space:nowrap;font-size:var(--font-size-meta)}code{overflow-wrap:anywhere}.unavailable{align-items:flex-start}
@media(max-width:900px){.integration-grid{grid-template-columns:1fr 1fr}.mapping-grid{grid-template-columns:1fr 1fr}}
@media(max-width:640px){.integration-grid,.form-grid,.mapping-grid{grid-template-columns:1fr}.integration-row{align-items:flex-start;flex-direction:column}}
</style>
