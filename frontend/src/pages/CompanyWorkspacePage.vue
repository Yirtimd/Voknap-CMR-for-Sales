<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute } from "vue-router";

import AIAssistantPanel from "../components/crm/AIAssistantPanel.vue";
import CompanyCardHeader from "../components/crm/CompanyCardHeader.vue";
import CompanyContacts from "../components/crm/CompanyContacts.vue";
import CompanyCurrentDeal from "../components/crm/CompanyCurrentDeal.vue";
import CompanyNextAction from "../components/crm/CompanyNextAction.vue";
import CompanyTasks from "../components/crm/CompanyTasks.vue";
import CompanyTimeline from "../components/crm/CompanyTimeline.vue";
import { crmStore } from "../stores/crm";

const route = useRoute();

onMounted(async () => {
  await crmStore.refreshAll();
  await crmStore.loadCompanyWorkspace(String(route.params.id));
});

const workspace = computed(() => crmStore.companyWorkspace.value);
</script>

<template>
  <section v-if="workspace" class="company-workspace-modal">
    <CompanyCardHeader :workspace="workspace" />

    <nav class="company-tabs workspace-tabs" aria-label="Company workspace sections">
      <a href="#timeline">Timeline</a>
      <a href="#ai">AI</a>
      <a href="#deals">Deals</a>
      <a href="#contacts">Contacts</a>
      <a href="#files">Files</a>
    </nav>

    <section class="workspace-modal-grid">
      <div class="workspace-primary">
        <CompanyTimeline id="timeline" :workspace="workspace" />
        <CompanyCurrentDeal id="deals" :workspace="workspace" />
      </div>

      <aside class="workspace-rail">
        <CompanyNextAction id="ai" :workspace="workspace" />
        <AIAssistantPanel title="AI рекомендует" preset="Что сделать по этой компании дальше?" />
        <CompanyContacts id="contacts" :workspace="workspace" />
        <CompanyTasks :workspace="workspace" />
        <section id="files" class="panel compact-panel">
          <h2>Files</h2>
          <p class="hint">Договоры, КП, счета и записи звонков будут собраны здесь.</p>
        </section>
      </aside>
    </section>
  </section>
</template>
