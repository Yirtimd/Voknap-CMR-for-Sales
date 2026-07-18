<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { crmStore } from "../stores/crm";

const channelFilter = ref("");
const statusFilter = ref("");
const visibleEvents = computed(() => crmStore.communicationEvents.value.filter((event) => {
  if (channelFilter.value && event.channel !== channelFilter.value) return false;
  if (statusFilter.value && event.status !== statusFilter.value) return false;
  return true;
}));

onMounted(async () => {
  await Promise.allSettled([
    crmStore.refreshAll(),
    crmStore.refreshActivities(),
    crmStore.refreshCommunication(),
    crmStore.refreshConnectors()
  ]);
});
</script>

<template>
  <section class="section-grid">
    <section class="panel">
      <h2>Центр коммуникаций</h2>

      <div class="inbox-toolbar">
        <select v-model="channelFilter">
          <option value="">Все каналы</option>
          <option value="email">Email</option>
          <option value="call">Звонки</option>
          <option value="calendar">Встречи</option>
          <option value="telegram">Telegram</option>
          <option value="whatsapp">WhatsApp</option>
        </select>
        <select v-model="statusFilter">
          <option value="">Все статусы</option>
          <option value="new">Не привязано</option>
          <option value="linked">Привязано</option>
          <option value="activity_created">Активность создана</option>
        </select>
        <button type="button" @click="crmStore.refreshCommunication">Обновить</button>
      </div>

      <form class="form-grid" @submit.prevent="crmStore.createCommunicationEvent()">
        <select v-model="crmStore.communicationEventForm.value.channel">
          <option value="email">Email</option>
          <option value="call">Звонок</option>
          <option value="calendar">Встреча</option>
          <option value="telegram">Telegram</option>
          <option value="whatsapp">WhatsApp</option>
        </select>
        <select v-model="crmStore.communicationEventForm.value.company_id">
          <option value="">Без компании</option>
          <option v-for="company in crmStore.companies.value" :key="company.id" :value="company.id">
            {{ company.name }}
          </option>
        </select>
        <input v-model="crmStore.communicationEventForm.value.sender" placeholder="Отправитель" />
        <input v-model="crmStore.communicationEventForm.value.subject" placeholder="Тема" required />
        <textarea v-model="crmStore.communicationEventForm.value.body" placeholder="Сообщение"></textarea>
        <button type="submit">Добавить входящее</button>
      </form>

      <article v-for="event in visibleEvents" :key="event.id" class="timeline-item">
        <span class="timeline-icon">{{ event.channel.slice(0, 2).toUpperCase() }}</span>
        <div>
          <header>
            <strong>{{ event.subject }}</strong>
            <small>{{ event.channel }} / {{ event.status }}</small>
          </header>
          <p v-if="event.body">{{ event.body }}</p>
          <small>{{ event.sender || "Отправитель неизвестен" }} · {{ new Date(event.occurred_at).toLocaleString("ru-RU") }}</small>
          <div class="form-grid compact-form">
            <select v-model="event.company_id">
              <option :value="null">Без компании</option>
              <option v-for="company in crmStore.companies.value" :key="company.id" :value="company.id">
                {{ company.name }}
              </option>
            </select>
            <select v-model="event.contact_id">
              <option :value="null">Без контакта</option>
              <option
                v-for="contact in crmStore.contacts.value.filter((item) => !event.company_id || item.company_id === event.company_id)"
                :key="contact.id"
                :value="contact.id"
              >
                {{ contact.name }}
              </option>
            </select>
            <select v-model="event.deal_id">
              <option :value="null">Без сделки</option>
              <option
                v-for="deal in crmStore.deals.value.filter((item) => !event.company_id || item.company_id === event.company_id)"
                :key="deal.id"
                :value="deal.id"
              >
                {{ deal.title }}
              </option>
            </select>
            <button type="button" @click="crmStore.linkCommunicationEvent(event)">Сохранить привязку</button>
            <button
              type="button"
              :disabled="!event.company_id || Boolean(event.activity_id)"
              @click="crmStore.createActivityFromCommunication(event.id)"
            >{{ event.activity_id ? "Активность создана" : "Создать активность" }}</button>
          </div>
        </div>
      </article>
      <section v-if="!visibleEvents.length" class="empty-state"><strong>Входящих событий нет</strong><p>Новые письма, звонки и встречи появятся здесь после синхронизации.</p></section>
    </section>

    <section class="panel">
      <h2>История синхронизации</h2>
      <article v-for="run in crmStore.connectorRuns.value.slice(0, 10)" :key="run.id" class="list-row">
        <span>{{ run.direction }} / {{ run.status }}</span>
        <small>Создано: {{ run.created_count }}</small>
      </article>
      <p v-if="!crmStore.connectorRuns.value.length" class="empty">Синхронизаций пока нет</p>
    </section>
  </section>
</template>
