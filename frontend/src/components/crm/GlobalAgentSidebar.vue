<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

import { crmStore } from "../../stores/crm";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: [] }>();

const messagesEl = ref<HTMLElement | null>(null);

const quickPrompts = [
  "Дай сводку по CRM",
  "Что нужно сделать сегодня?",
  "Найди риски в воронке",
  "Какие сделки без next action?",
  "Создай задачу позвонить клиенту",
  "Подготовь план дня менеджера"
];

watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) return;
    await crmStore.refreshAgent();
    await nextTick();
    messagesEl.value?.scrollTo({ top: messagesEl.value.scrollHeight });
  }
);

async function send(message?: string) {
  if (message) crmStore.agentForm.value.message = message;
  if (!crmStore.agentForm.value.message.trim()) return;
  await crmStore.sendAgentMessage();
  await nextTick();
  messagesEl.value?.scrollTo({ top: messagesEl.value.scrollHeight, behavior: "smooth" });
}

function formatPayload(payload: Record<string, unknown>) {
  return JSON.stringify(payload, null, 2);
}
</script>

<template>
  <aside v-if="open" class="agent-sidebar">
    <header class="agent-sidebar-head">
      <div>
        <p class="eyebrow">Global AI Agent</p>
        <h2>Агент продаж</h2>
      </div>
      <button class="secondary" type="button" @click="emit('close')">Close</button>
    </header>

    <section class="agent-context">
      <div><strong>{{ crmStore.openTasks.value.length }}</strong><small>Open tasks</small></div>
      <div><strong>{{ crmStore.deals.value.length }}</strong><small>Deals</small></div>
      <div><strong>{{ crmStore.money(crmStore.totalPipeline.value) }}</strong><small>Pipeline</small></div>
    </section>

    <section class="agent-quick">
      <button
        v-for="prompt in quickPrompts"
        :key="prompt"
        class="secondary"
        type="button"
        @click="send(prompt)"
      >
        {{ prompt }}
      </button>
    </section>

    <section ref="messagesEl" class="agent-messages">
      <article v-for="message in crmStore.agentHistory.value" :key="message.id" class="agent-message" :class="message.role">
        <strong>{{ message.role === "user" ? "Вы" : "Агент" }}</strong>
        <p>{{ message.content }}</p>
      </article>
      <p v-if="!crmStore.agentHistory.value.length" class="empty">Истории пока нет. Выберите быстрый запрос или напишите сообщение.</p>
    </section>

    <section v-if="crmStore.agentActions.value.length" class="agent-actions">
      <h3>Действия</h3>
      <article v-for="action in crmStore.agentActions.value" :key="action.id" class="action-card">
        <header>
          <strong>{{ action.action_type }}</strong>
          <small>{{ action.status }}</small>
        </header>
        <pre>{{ formatPayload(action.payload) }}</pre>
        <div v-if="action.status === 'pending'" class="button-row">
          <button type="button" @click="crmStore.confirmAgentAction(action.id)">Подтвердить</button>
          <button class="secondary" type="button" @click="crmStore.rejectAgentAction(action.id)">Отклонить</button>
        </div>
      </article>
    </section>

    <form class="agent-composer" @submit.prevent="send()">
      <textarea v-model="crmStore.agentForm.value.message" placeholder="Спросить глобального агента..." rows="3"></textarea>
      <button type="submit" :disabled="crmStore.isLoading.value">Send</button>
    </form>
  </aside>
</template>
