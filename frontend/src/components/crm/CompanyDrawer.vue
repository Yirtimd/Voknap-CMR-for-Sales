<script setup lang="ts">
import { computed } from "vue";

import type { Company } from "../../types";
import { crmStore } from "../../stores/crm";
import AIAssistantPanel from "./AIAssistantPanel.vue";
import CompanyCardHeader from "./CompanyCardHeader.vue";
import CompanyContacts from "./CompanyContacts.vue";
import CompanyCurrentDeal from "./CompanyCurrentDeal.vue";
import CompanyNextAction from "./CompanyNextAction.vue";
import CompanyTasks from "./CompanyTasks.vue";
import CompanyTimeline from "./CompanyTimeline.vue";

const props = defineProps<{ company: Company | null }>();
const emit = defineEmits<{ close: [] }>();

const workspace = computed(() =>
  props.company && crmStore.companyWorkspace.value?.company.id === props.company.id
    ? crmStore.companyWorkspace.value
    : null
);

function close() {
  emit("close");
}
</script>

<template>
  <div v-if="company" class="workspace-modal-backdrop" @click.self="close">
    <section v-if="workspace" class="company-workspace-modal company-workspace-overlay" role="dialog" aria-modal="true">
      <button class="secondary modal-close" type="button" @click="close">Close</button>

      <CompanyCardHeader :workspace="workspace" />

      <nav class="company-tabs workspace-tabs" aria-label="Company workspace sections">
        <a href="#modal-timeline">Timeline</a>
        <a href="#modal-ai">AI</a>
        <a href="#modal-deals">Deals</a>
        <a href="#modal-contacts">Contacts</a>
        <a href="#modal-files">Files</a>
      </nav>

      <section class="workspace-modal-grid">
        <div class="workspace-primary">
          <CompanyTimeline id="modal-timeline" :workspace="workspace" />
          <CompanyCurrentDeal id="modal-deals" :workspace="workspace" />
        </div>

        <aside class="workspace-rail">
          <CompanyNextAction id="modal-ai" :workspace="workspace" />
          <AIAssistantPanel title="AI рекомендует" preset="Что сделать по этой компании дальше?" />
          <CompanyContacts id="modal-contacts" :workspace="workspace" />
          <CompanyTasks :workspace="workspace" />
          <section id="modal-files" class="panel compact-panel">
            <h2>Files</h2>
            <p class="hint">Договоры, КП, счета и записи звонков будут собраны здесь.</p>
          </section>
        </aside>
      </section>
    </section>

    <section v-else class="company-workspace-modal company-workspace-loading" role="dialog" aria-modal="true">
      <button class="secondary modal-close" type="button" @click="close">Close</button>
      <p class="eyebrow">Workspace Modal</p>
      <h2>{{ company.name }}</h2>
      <p class="hint">Загружаю рабочее пространство компании...</p>
    </section>
  </div>
</template>
