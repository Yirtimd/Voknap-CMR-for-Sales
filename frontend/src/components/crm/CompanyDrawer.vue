<script setup lang="ts">
import { computed } from "vue";

import type { Company } from "../../types";
import { crmStore } from "../../stores/crm";
import AIAssistantPanel from "./AIAssistantPanel.vue";

const props = defineProps<{ company: Company | null }>();
const emit = defineEmits<{ close: [] }>();

const workspace = computed(() =>
  props.company && crmStore.companyWorkspace.value?.company.id === props.company.id
    ? crmStore.companyWorkspace.value
    : null
);

const deals = computed(() => workspace.value?.deals ?? crmStore.deals.value.filter((deal) => deal.company_id === props.company?.id));
const tasks = computed(() => workspace.value?.tasks ?? crmStore.tasks.value.filter((task) => task.company_id === props.company?.id));
const activities = computed(() => workspace.value?.activities ?? crmStore.activities.value.filter((item) => item.company_id === props.company?.id));
const openTasks = computed(() => tasks.value.filter((task) => !task.done_at));
const pipeline = computed(() => deals.value.reduce((sum, deal) => sum + Number(deal.amount ?? 0), 0));
const health = computed(() => Math.min(98, 58 + deals.value.length * 9 + openTasks.value.length * 4));
const nextAction = computed(() => openTasks.value[0]?.title ?? (deals.value.length ? "Запланировать follow-up" : "Создать первую сделку"));

function close() {
  emit("close");
}
</script>

<template>
  <aside v-if="company" class="drawer company-drawer">
    <header>
      <div>
        <p class="eyebrow">Company Drawer</p>
        <h2>{{ company.name }}</h2>
        <p>{{ company.industry ?? "Отрасль не указана" }}</p>
      </div>
      <button class="secondary" type="button" @click="close">Close</button>
    </header>

    <nav class="drawer-tabs">
      <a href="#drawer-overview">Overview</a>
      <a href="#drawer-timeline">Timeline</a>
      <a href="#drawer-tasks">Tasks</a>
      <a href="#drawer-ai">AI</a>
      <a href="#drawer-deals">Deals</a>
    </nav>

    <section id="drawer-overview" class="drawer-section">
      <h3>Overview</h3>
      <dl class="drawer-facts grid-facts">
        <div><dt>Health</dt><dd>{{ health }}</dd></div>
        <div><dt>Pipeline</dt><dd>{{ crmStore.money(pipeline) }}</dd></div>
        <div><dt>Open Tasks</dt><dd>{{ openTasks.length }}</dd></div>
        <div><dt>Next Action</dt><dd>{{ nextAction }}</dd></div>
      </dl>
      <div class="quick-actions">
        <button class="secondary" type="button">Call</button>
        <button class="secondary" type="button">Email</button>
        <button class="secondary" type="button">Task</button>
        <button type="button">Ask AI</button>
      </div>
    </section>

    <section id="drawer-timeline" class="drawer-section">
      <h3>Timeline</h3>
      <article v-for="activity in activities.slice(0, 8)" :key="String(activity.id)" class="timeline-item">
        <span class="timeline-icon">{{ String(activity.type).slice(0, 2) }}</span>
        <div>
          <header>
            <strong>{{ activity.title }}</strong>
            <small>{{ activity.type }}</small>
          </header>
          <p v-if="activity.description">{{ activity.description }}</p>
        </div>
      </article>
      <p v-if="!activities.length" class="empty">Истории пока нет</p>
    </section>

    <section id="drawer-tasks" class="drawer-section">
      <h3>Tasks</h3>
      <article v-for="task in openTasks.slice(0, 6)" :key="task.id" class="task-row drawer-task">
        <span class="status-dot"></span>
        <div>
          <strong>{{ task.title }}</strong>
          <small>{{ task.description ?? "Без описания" }}</small>
        </div>
        <button class="secondary" type="button" @click="crmStore.toggleTask(task)">Done</button>
      </article>
      <p v-if="!openTasks.length" class="empty">Открытых задач нет</p>
    </section>

    <section id="drawer-ai" class="drawer-section drawer-ai">
      <AIAssistantPanel title="AI" preset="Что делать дальше по этой компании?" />
    </section>

    <section id="drawer-deals" class="drawer-section">
      <h3>Deals</h3>
      <article v-for="deal in deals" :key="deal.id" class="list-row">
        <span>{{ deal.title }}</span>
        <small>{{ crmStore.money(deal.amount) }}</small>
      </article>
      <p v-if="!deals.length" class="empty">Сделок пока нет</p>
    </section>
  </aside>
</template>
