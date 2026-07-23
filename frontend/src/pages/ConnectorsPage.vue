<script setup lang="ts">
import { onMounted } from "vue";

import { statusLabel } from "../design-system/statusDictionary";
import { crmStore } from "../stores/crm";

onMounted(() => {
  void crmStore.refreshConnectors();
});

function applyEmailProvider() {
  const provider = crmStore.connectorAccountForm.value.email_provider;
  if (provider === "gmail") {
    crmStore.connectorAccountForm.value.host = "imap.gmail.com";
    crmStore.connectorAccountForm.value.port = 993;
  }
}
</script>

<template>
  <section class="section-grid">
    <section class="panel">
      <h2>Доступные коннекторы</h2>
      <div v-for="connector in crmStore.connectorDefinitions.value" :key="connector.code" class="list-row">
        <span>{{ connector.title }}</span>
        <small>{{ statusLabel(connector.status, "connector") }}</small>
      </div>
    </section>

    <form class="panel" @submit.prevent="crmStore.createConnectorAccount">
      <h2>Подключить</h2>
      <label>Коннектор
        <select v-model="crmStore.connectorAccountForm.value.connector_code">
          <option v-for="connector in crmStore.connectorDefinitions.value" :key="connector.code" :value="connector.code">
            {{ connector.title }}
          </option>
        </select>
      </label>
      <label>Название<input v-model="crmStore.connectorAccountForm.value.title" /></label>
      <template v-if="crmStore.connectorAccountForm.value.connector_code === 'email'">
        <label>Провайдер
          <select v-model="crmStore.connectorAccountForm.value.email_provider" @change="applyEmailProvider">
            <option value="gmail">Gmail / Google Workspace</option>
            <option value="custom">Другой IMAP</option>
          </select>
        </label>
        <label>IMAP host<input v-model="crmStore.connectorAccountForm.value.host" required /></label>
        <label>IMAP port<input v-model.number="crmStore.connectorAccountForm.value.port" type="number" min="1" max="65535" required /></label>
        <label>Email / login<input v-model="crmStore.connectorAccountForm.value.username" inputmode="email" autocomplete="username" required /></label>
        <label>App password<input v-model="crmStore.connectorAccountForm.value.password" type="password" autocomplete="new-password" required /></label>
        <label>Папка<input v-model="crmStore.connectorAccountForm.value.folder" required /></label>
        <label class="checkbox-row"><input v-model="crmStore.connectorAccountForm.value.use_ssl" type="checkbox" /> SSL/TLS</label>
        <small class="form-hint">Пароль проверяется через IMAP и хранится зашифрованным. Для Gmail используйте App Password. Microsoft 365 требует отдельного OAuth-подключения.</small>
      </template>
      <button type="submit" :disabled="crmStore.isLoading.value">
        {{ crmStore.connectorAccountForm.value.connector_code === "email" ? "Проверить и подключить" : "Подключить" }}
      </button>
    </form>

    <section class="panel wide">
      <h2>Подключения</h2>
      <div v-for="account in crmStore.connectorAccounts.value" :key="account.id" class="entity-row">
        <div>
          <strong>{{ account.title }}</strong>
          <small>{{ account.connector_code }} · {{ account.status }}<template v-if="account.sync_cursor"> · UID {{ account.sync_cursor }}</template></small>
        </div>
        <div class="connector-actions">
          <small>{{ account.last_sync_at ? new Date(account.last_sync_at).toLocaleString() : "sync not run" }}</small>
          <button
            v-if="account.status !== 'placeholder' && account.connector_code !== 'csv'"
            type="button"
            :disabled="crmStore.isLoading.value"
            @click="crmStore.syncConnectorAccount(account.id)"
          >Sync now</button>
        </div>
      </div>
      <p v-if="!crmStore.connectorAccounts.value.length" class="empty">Подключений пока нет</p>
    </section>

    <form class="panel" @submit.prevent="crmStore.importCsv">
      <h2>CSV импорт лидов</h2>
      <label>CSV account
        <select v-model="crmStore.csvImportForm.value.account_id" required>
          <option value="">Выбрать</option>
          <option
            v-for="account in crmStore.connectorAccounts.value.filter((item) => item.connector_code === 'csv')"
            :key="account.id"
            :value="account.id"
          >
            {{ account.title }}
          </option>
        </select>
      </label>
      <label>CSV<textarea v-model="crmStore.csvImportForm.value.csv_text" class="large-textarea"></textarea></label>
      <button type="submit">Импортировать</button>
    </form>

    <section class="panel">
      <h2>CSV экспорт</h2>
      <button type="button" @click="crmStore.exportCsv">Сформировать экспорт</button>
      <textarea v-if="crmStore.csvExport.value" class="large-textarea export-box" readonly :value="crmStore.csvExport.value.csv_text"></textarea>
    </section>

    <section class="panel wide">
      <h2>История синхронизаций</h2>
      <div v-for="run in crmStore.connectorRuns.value" :key="run.id" class="entity-row">
        <div>
          <strong>{{ run.direction }} · {{ run.status }}</strong>
          <small>{{ run.message ?? "no message" }}</small>
        </div>
        <div class="connector-actions">
          <small>created {{ run.created_count }} · failed {{ run.failed_count }}</small>
          <button
            v-if="run.status === 'failed' || run.status === 'retry_scheduled'"
            type="button"
            @click="crmStore.retryConnectorRun(run.id)"
          >Retry</button>
        </div>
      </div>
      <p v-if="!crmStore.connectorRuns.value.length" class="empty">Синхронизаций пока нет</p>
    </section>
  </section>
</template>
