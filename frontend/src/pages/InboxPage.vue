<script setup lang="ts">
import { onMounted } from "vue";

import { crmStore } from "../stores/crm";

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
      <h2>Communication Hub</h2>

      <form class="form-grid" @submit.prevent="crmStore.createCommunicationEvent()">
        <select v-model="crmStore.communicationEventForm.value.channel">
          <option value="email">Email</option>
          <option value="call">Call</option>
          <option value="calendar">Meeting</option>
          <option value="telegram">Telegram</option>
          <option value="whatsapp">WhatsApp</option>
        </select>
        <select v-model="crmStore.communicationEventForm.value.company_id">
          <option value="">No company</option>
          <option v-for="company in crmStore.companies.value" :key="company.id" :value="company.id">
            {{ company.name }}
          </option>
        </select>
        <input v-model="crmStore.communicationEventForm.value.sender" placeholder="Sender" />
        <input v-model="crmStore.communicationEventForm.value.subject" placeholder="Subject" />
        <textarea v-model="crmStore.communicationEventForm.value.body" placeholder="Message"></textarea>
        <button type="submit">Create incoming</button>
      </form>

      <article v-for="event in crmStore.communicationEvents.value" :key="event.id" class="timeline-item">
        <span class="timeline-icon">{{ event.channel.slice(0, 2).toUpperCase() }}</span>
        <div>
          <header>
            <strong>{{ event.subject }}</strong>
            <small>{{ event.channel }} / {{ event.status }}</small>
          </header>
          <p v-if="event.ai_summary">{{ event.ai_summary }}</p>
          <p v-else-if="event.body">{{ event.body }}</p>
          <div class="form-grid compact-form">
            <select v-model="event.company_id">
              <option :value="null">No company</option>
              <option v-for="company in crmStore.companies.value" :key="company.id" :value="company.id">
                {{ company.name }}
              </option>
            </select>
            <select v-model="event.contact_id">
              <option :value="null">No contact</option>
              <option
                v-for="contact in crmStore.contacts.value.filter((item) => !event.company_id || item.company_id === event.company_id)"
                :key="contact.id"
                :value="contact.id"
              >
                {{ contact.name }}
              </option>
            </select>
            <select v-model="event.deal_id">
              <option :value="null">No deal</option>
              <option
                v-for="deal in crmStore.deals.value.filter((item) => !event.company_id || item.company_id === event.company_id)"
                :key="deal.id"
                :value="deal.id"
              >
                {{ deal.title }}
              </option>
            </select>
            <button type="button" @click="crmStore.linkCommunicationEvent(event)">Link</button>
            <button type="button" @click="crmStore.createActivityFromCommunication(event.id)">Create activity</button>
            <button type="button" @click="crmStore.refreshCommunicationSummary(event.id)">AI summary</button>
          </div>
        </div>
      </article>
      <p v-if="!crmStore.communicationEvents.value.length" class="empty">Входящих событий пока нет</p>
    </section>

    <section class="panel">
      <h2>Connector Runs</h2>
      <article v-for="run in crmStore.connectorRuns.value.slice(0, 10)" :key="run.id" class="list-row">
        <span>{{ run.direction }} / {{ run.status }}</span>
        <small>{{ run.created_count }} created</small>
      </article>
      <p v-if="!crmStore.connectorRuns.value.length" class="empty">Синхронизаций пока нет</p>
    </section>
  </section>
</template>
