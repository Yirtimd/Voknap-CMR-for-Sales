<script setup lang="ts">
import { onMounted } from "vue";

import { crmStore } from "../stores/crm";

onMounted(() => {
  void crmStore.refreshConnectors();
});
</script>

<template>
  <section class="section-grid">
    <section class="panel">
      <h2>Доступные коннекторы</h2>
      <div v-for="connector in crmStore.connectorDefinitions.value" :key="connector.code" class="list-row">
        <span>{{ connector.title }}</span>
        <small>{{ connector.status }}</small>
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
      <button type="submit">Подключить</button>
    </form>

    <section class="panel wide">
      <h2>Подключения</h2>
      <div v-for="account in crmStore.connectorAccounts.value" :key="account.id" class="entity-row">
        <div>
          <strong>{{ account.title }}</strong>
          <small>{{ account.connector_code }} · {{ account.status }}</small>
        </div>
        <small>{{ account.last_sync_at ?? "sync not run" }}</small>
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
        <small>created {{ run.created_count }} · failed {{ run.failed_count }}</small>
      </div>
      <p v-if="!crmStore.connectorRuns.value.length" class="empty">Синхронизаций пока нет</p>
    </section>
  </section>
</template>
