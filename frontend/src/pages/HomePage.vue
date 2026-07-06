<script setup lang="ts">
import { computed, onMounted } from "vue";

import { crmStore } from "../stores/crm";
import type { Deal, Task } from "../types";

type WorkItem = {
  id: string;
  tone: "critical" | "warning" | "good" | "neutral";
  label: string;
  title: string;
  meta: string;
  action: string;
  to: string;
};

onMounted(async () => {
  await crmStore.refreshAll();
  await Promise.allSettled([crmStore.refreshAgent(), crmStore.refreshActivities()]);
});

function companyName(companyId: string | null) {
  return crmStore.companies.value.find((company) => company.id === companyId)?.name ?? "Компания";
}

function formatDue(value: string | null) {
  if (!value) return "Без срока";
  const due = new Date(value);
  if (Number.isNaN(due.getTime())) return value;
  const today = new Date();
  const startToday = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  const startDue = new Date(due.getFullYear(), due.getMonth(), due.getDate()).getTime();
  const days = Math.round((startDue - startToday) / 86400000);
  if (days < 0) return `Просрочено ${Math.abs(days)} дн.`;
  if (days === 0) return "Сегодня";
  if (days === 1) return "Завтра";
  return due.toLocaleDateString("ru-RU", { day: "2-digit", month: "short" });
}

function taskToItem(task: Task): WorkItem {
  const due = task.due_at ? Date.parse(task.due_at) : 0;
  const overdue = Boolean(task.due_at && due < Date.now());
  return {
    id: `task-${task.id}`,
    tone: overdue ? "critical" : "warning",
    label: overdue ? "Overdue" : "Task",
    title: task.title,
    meta: `${companyName(task.company_id)} · ${formatDue(task.due_at)}`,
    action: "Done",
    to: "/tasks"
  };
}

function dealToItem(deal: Deal): WorkItem {
  return {
    id: `deal-${deal.id}`,
    tone: "good",
    label: "Deal",
    title: `Продвинуть: ${deal.title}`,
    meta: `${companyName(deal.company_id)} · ${crmStore.money(deal.amount)}`,
    action: "Open",
    to: "/deals"
  };
}

const overdueTasks = computed(() =>
  crmStore.tasks.value
    .filter((task) => !task.done_at && task.due_at && Date.parse(task.due_at) < Date.now())
    .sort((left, right) => Date.parse(left.due_at ?? "") - Date.parse(right.due_at ?? ""))
);

const todayTasks = computed(() => {
  const today = new Date();
  return crmStore.tasks.value.filter((task) => {
    if (task.done_at || !task.due_at) return false;
    const due = new Date(task.due_at);
    return due.toDateString() === today.toDateString();
  });
});

const priorityDeals = computed(() =>
  [...crmStore.deals.value]
    .filter((deal) => deal.status !== "won")
    .sort((left, right) => Number(right.amount ?? 0) - Number(left.amount ?? 0))
    .slice(0, 3)
);

const workQueue = computed<WorkItem[]>(() => {
  const queue = [...overdueTasks.value.map(taskToItem), ...todayTasks.value.map(taskToItem), ...priorityDeals.value.map(dealToItem)];
  if (queue.length) return queue.slice(0, 7);
  return [
    {
      id: "sync",
      tone: "neutral",
      label: "Workspace",
      title: "Синхронизировать коммуникации",
      meta: "Inbox · Email, звонки, комментарии",
      action: "Open",
      to: "/inbox"
    }
  ];
});

const aiRecommendation = computed(() => {
  const firstTask = overdueTasks.value[0] ?? todayTasks.value[0];
  if (firstTask) return `Начать с "${firstTask.title}" для ${companyName(firstTask.company_id)}. Это снимает риск просрочки и возвращает сделку в работу.`;
  const firstDeal = priorityDeals.value[0];
  if (firstDeal) return `Открыть ${companyName(firstDeal.company_id)} и назначить next action по сделке "${firstDeal.title}".`;
  return "Создать первую компанию, контакт и задачу. CRM начнет собирать рабочую очередь.";
});
</script>

<template>
  <section class="stack">
    <section class="home-brief action-brief">
      <div>
        <p class="eyebrow">Today Workspace</p>
        <h1>Сегодня я работаю</h1>
        <p>{{ aiRecommendation }}</p>
      </div>
      <div class="button-row">
        <RouterLink class="button-link" to="/companies">Company Workspace</RouterLink>
        <RouterLink class="button-link secondary-link" to="/deals">Pipeline</RouterLink>
      </div>
    </section>

    <section class="workspace-grid">
      <section class="panel wide action-feed">
        <header class="panel-head">
          <div>
            <p class="eyebrow">Next Best Actions</p>
            <h2>Очередь работы</h2>
          </div>
          <small>{{ crmStore.openTasks.value.length }} открытых задач · {{ crmStore.money(crmStore.totalPipeline.value) }}</small>
        </header>

        <article v-for="item in workQueue" :key="item.id" class="action-row" :class="item.tone">
          <span class="status-dot"></span>
          <div>
            <strong>{{ item.title }}</strong>
            <small>{{ item.meta }}</small>
          </div>
          <RouterLink class="button-link secondary-link" :to="item.to">{{ item.action }}</RouterLink>
        </article>
      </section>

      <section class="panel">
        <h2>AI рекомендует</h2>
        <p class="answer-text">{{ aiRecommendation }}</p>
        <div class="button-row">
          <RouterLink class="button-link" to="/home">Next Action</RouterLink>
          <RouterLink class="button-link secondary-link" to="/knowledge">Context</RouterLink>
        </div>
      </section>

      <section class="panel">
        <h2>Pipeline Focus</h2>
        <article v-for="deal in priorityDeals" :key="deal.id" class="compact-deal">
          <strong>{{ deal.title }}</strong>
          <small>{{ companyName(deal.company_id) }}</small>
          <div class="deal-meta-line">
            <span>{{ crmStore.money(deal.amount) }}</span>
            <span>Health {{ Math.min(96, 64 + Number(deal.amount ?? 0) / 5000).toFixed(0) }}</span>
          </div>
        </article>
        <p v-if="!priorityDeals.length" class="empty">Нет активных сделок</p>
      </section>
    </section>
  </section>
</template>
