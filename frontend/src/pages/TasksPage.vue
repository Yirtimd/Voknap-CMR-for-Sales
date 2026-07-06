<script setup lang="ts">
import { computed } from "vue";

import { crmStore } from "../stores/crm";
import type { Task } from "../types";

function companyName(companyId: string) {
  return crmStore.companies.value.find((company) => company.id === companyId)?.name ?? "Компания";
}

function dayKey(task: Task) {
  if (!task.due_at) return "open";
  const due = new Date(task.due_at);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const taskDay = new Date(due.getFullYear(), due.getMonth(), due.getDate()).getTime();
  if (taskDay < today) return "overdue";
  if (taskDay === today) return "today";
  if (taskDay === today + 86400000) return "tomorrow";
  return "open";
}

const groups = computed(() => {
  const open = crmStore.tasks.value.filter((task) => !task.done_at);
  return [
    { code: "today", title: "Today", items: open.filter((task) => dayKey(task) === "today") },
    { code: "tomorrow", title: "Tomorrow", items: open.filter((task) => dayKey(task) === "tomorrow") },
    { code: "overdue", title: "Overdue", items: open.filter((task) => dayKey(task) === "overdue") },
    { code: "open", title: "Later / No Date", items: open.filter((task) => dayKey(task) === "open") }
  ];
});
</script>

<template>
  <section class="stack">
    <section class="workspace-hero compact-hero">
      <div>
        <p class="eyebrow">Execution Workspace</p>
        <h1>Работаю с задачами</h1>
        <p>Задачи сгруппированы по времени, а не списком записей из базы.</p>
      </div>
      <RouterLink class="button-link secondary-link" to="/companies">К клиентам</RouterLink>
    </section>

    <section class="task-board">
      <section v-for="group in groups" :key="group.code" class="panel task-group" :class="group.code">
        <header class="panel-head">
          <h2>{{ group.title }}</h2>
          <small>{{ group.items.length }}</small>
        </header>
        <article v-for="task in group.items" :key="task.id" class="task-row">
          <span class="status-dot"></span>
          <div>
            <strong>{{ task.title }}</strong>
            <small>{{ companyName(task.company_id) }} · {{ task.description ?? "Без описания" }}</small>
          </div>
          <button class="secondary" type="button" @click="crmStore.toggleTask(task)">Done</button>
        </article>
        <p v-if="!group.items.length" class="empty">Пусто</p>
      </section>
    </section>

    <details class="panel create-drawer">
      <summary>New Task</summary>
      <form class="compact-form" @submit.prevent="crmStore.createTask">
        <label>Компания
          <select v-model="crmStore.taskForm.value.company_id" required>
            <option value="">Выбрать</option>
            <option v-for="company in crmStore.companies.value" :key="company.id" :value="company.id">{{ company.name }}</option>
          </select>
        </label>
        <label>Название<input v-model="crmStore.taskForm.value.title" /></label>
        <label>Описание<textarea v-model="crmStore.taskForm.value.description"></textarea></label>
        <label>Сделка
          <select v-model="crmStore.taskForm.value.deal_id">
            <option value="">Без сделки</option>
            <option
              v-for="deal in crmStore.deals.value.filter((item) => item.company_id === crmStore.taskForm.value.company_id)"
              :key="deal.id"
              :value="deal.id"
            >{{ deal.title }}</option>
          </select>
        </label>
        <label>Срок<input v-model="crmStore.taskForm.value.due_at" type="datetime-local" /></label>
        <button type="submit">Создать задачу</button>
      </form>
    </details>
  </section>
</template>
