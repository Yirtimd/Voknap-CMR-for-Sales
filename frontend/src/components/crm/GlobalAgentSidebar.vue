<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

import { crmStore } from "../../stores/crm";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: [] }>();

const messagesEl = ref<HTMLElement | null>(null);

const importantPrompts = [
  "Что нужно сделать сегодня?",
  "Найди риски в воронке",
  "Какие сделки без следующего шага?",
  "Подготовь план дня менеджера"
];

const recentPrompts = [
  { text: "Дай сводку по CRM", time: "10:30" },
  { text: "Какие сделки без следующего шага?", time: "Вчера" },
  { text: "Создай задачу позвонить клиенту", time: "Вчера" }
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
      <div class="agent-title">
        <h2>AI Агент</h2>
        <p>Глобальный помощник</p>
      </div>
      <button class="secondary agent-close" type="button" aria-label="Закрыть AI-агента" @click="emit('close')">Закрыть</button>
    </header>

    <section class="agent-card agent-summary">
      <header>
        <strong>Сводка по CRM</strong>
        <button type="button" @click="send('Дай сводку по CRM')">›</button>
      </header>
      <div class="agent-context">
        <div><strong>{{ crmStore.openTasks.value.length }}</strong><small>Открытые задачи</small></div>
        <div><strong>{{ crmStore.deals.value.length }}</strong><small>Сделки</small></div>
        <div><strong>{{ crmStore.money(crmStore.totalPipeline.value) }}</strong><small>Портфель</small></div>
      </div>
    </section>

    <section class="agent-card agent-important">
      <h3>Что важно</h3>
      <button
        v-for="prompt in importantPrompts"
        :key="prompt"
        type="button"
        @click="send(prompt)"
      >
        <span class="prompt-icon">⌘</span>
        <strong>{{ prompt }}</strong>
        <span>›</span>
      </button>
    </section>

    <section ref="messagesEl" class="agent-messages">
      <article v-for="message in crmStore.agentHistory.value" :key="message.id" class="agent-message" :class="message.role">
        <strong>{{ message.role === "user" ? "Вы" : "Агент" }}</strong>
        <p>{{ message.content }}</p>
      </article>
      <p v-if="!crmStore.agentHistory.value.length" class="empty">Истории пока нет. Выберите быстрый запрос или напишите сообщение.</p>
    </section>

    <section class="agent-card agent-recent">
      <h3>Недавние запросы</h3>
      <button v-for="prompt in recentPrompts" :key="prompt.text" type="button" @click="send(prompt.text)">
        <span class="prompt-icon doc">□</span>
        <strong>{{ prompt.text }}</strong>
        <small>{{ prompt.time }}</small>
      </button>
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

    <form class="agent-card agent-composer" @submit.prevent="send()">
      <div class="composer-shell">
        <textarea v-model="crmStore.agentForm.value.message" placeholder="Спросите что угодно..." rows="2"></textarea>
        <button type="submit" :disabled="crmStore.isLoading.value">›</button>
      </div>
      <small>AI может ошибаться</small>
    </form>
  </aside>
</template>
