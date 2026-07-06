<script setup lang="ts">
import { crmStore } from "../../stores/crm";

defineProps<{ title?: string; preset?: string }>();
</script>

<template>
  <section class="panel ai-panel">
    <h2>{{ title ?? "AI Assistant" }}</h2>
    <div class="ai-command-grid">
      <button type="button" @click="crmStore.agentForm.value.message = 'Дай краткое резюме клиента'; crmStore.sendAgentMessage()">Summarize</button>
      <button class="secondary" type="button" @click="crmStore.agentForm.value.message = 'Сгенерируй email клиенту'; crmStore.sendAgentMessage()">Generate Email</button>
      <button class="secondary" type="button" @click="crmStore.agentForm.value.message = 'Сгенерируй КП'; crmStore.sendAgentMessage()">Proposal</button>
      <button class="secondary" type="button" @click="crmStore.agentForm.value.message = 'Выдели meeting notes'; crmStore.sendAgentMessage()">Meeting Notes</button>
      <button class="secondary" type="button" @click="crmStore.agentForm.value.message = preset ?? 'What should I do next?'; crmStore.sendAgentMessage()">Next Action</button>
      <button class="secondary" type="button" @click="crmStore.agentForm.value.message = 'Проанализируй риски сделки'; crmStore.sendAgentMessage()">Analyze Risks</button>
    </div>
    <p v-if="crmStore.agentLastResponse.value" class="answer-text">{{ crmStore.agentLastResponse.value.answer }}</p>
  </section>
</template>
