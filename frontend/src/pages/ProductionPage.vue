<script setup lang="ts">
import { onMounted } from "vue";

import { crmStore } from "../stores/crm";

onMounted(() => {
  void crmStore.refreshProduction();
});

function pretty(value: unknown) {
  return JSON.stringify(value, null, 2);
}
</script>

<template>
  <section class="stack">
    <div class="metric-grid">
      <div v-for="(value, key) in crmStore.productionOverview.value?.counts ?? {}" :key="key" class="metric">
        <span>{{ key }}</span>
        <strong>{{ value }}</strong>
      </div>
    </div>

    <section class="section-grid">
      <form class="panel" @submit.prevent="crmStore.updateTenantPlan">
        <h2>Тариф и лимиты</h2>
        <label>Plan<input v-model="crmStore.planForm.value.plan_code" /></label>
        <label>Users<input v-model.number="crmStore.planForm.value.users_limit" type="number" /></label>
        <label>Leads<input v-model.number="crmStore.planForm.value.leads_limit" type="number" /></label>
        <label>Documents<input v-model.number="crmStore.planForm.value.documents_limit" type="number" /></label>
        <label>AI requests<input v-model.number="crmStore.planForm.value.ai_requests_limit" type="number" /></label>
        <button type="submit">Сохранить тариф</button>
      </form>

      <form class="panel" @submit.prevent="crmStore.createFeatureFlag">
        <h2>Feature flag</h2>
        <label>Code<input v-model="crmStore.featureFlagForm.value.code" /></label>
        <label>Title<input v-model="crmStore.featureFlagForm.value.title" /></label>
        <label class="check-row">
          <input v-model="crmStore.featureFlagForm.value.enabled" type="checkbox" />
          Enabled
        </label>
        <button type="submit">Сохранить flag</button>
      </form>

      <section class="panel">
        <h2>Flags</h2>
        <div v-for="flag in crmStore.featureFlags.value" :key="flag.id" class="entity-row">
          <div>
            <strong>{{ flag.title }}</strong>
            <small>{{ flag.code }} · {{ flag.enabled ? "enabled" : "disabled" }}</small>
          </div>
          <button class="secondary" type="button" @click="crmStore.toggleFeatureFlag(flag)">
            {{ flag.enabled ? "Disable" : "Enable" }}
          </button>
        </div>
      </section>

      <section class="panel">
        <h2>Data export</h2>
        <div class="button-row">
          <button type="button" @click="crmStore.exportTenantData">Export JSON</button>
          <button class="secondary" type="button" @click="crmStore.createAuditMarker">Audit marker</button>
        </div>
        <textarea
          v-if="crmStore.tenantExport.value"
          class="large-textarea export-box"
          readonly
          :value="pretty(crmStore.tenantExport.value.data)"
        ></textarea>
      </section>

      <section class="panel wide">
        <h2>Audit log</h2>
        <div v-for="row in crmStore.auditLogs.value" :key="row.id" class="entity-row">
          <div>
            <strong>{{ row.action }}</strong>
            <small>{{ row.entity_type ?? "system" }} · {{ row.created_at }}</small>
          </div>
          <small>{{ row.entity_id ?? "" }}</small>
        </div>
        <p v-if="!crmStore.auditLogs.value.length" class="empty">Audit пуст</p>
      </section>
    </section>
  </section>
</template>
