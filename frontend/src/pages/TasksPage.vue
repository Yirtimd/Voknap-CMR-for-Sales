<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import EntityCrudDrawer from "../components/crm/EntityCrudDrawer.vue";
import { crmStore } from "../stores/crm";
import type { Task } from "../types";

type StatusFilter = "all" | "open" | "overdue" | "completed";
type TaskGroup = { code: string; title: string; items: Task[] };

const route = useRoute();
const router = useRouter();
const createDrawer = ref<HTMLDetailsElement | null>(null);
const selectedTask = ref<Task | null>(null);
const isTaskCrudOpen = ref(false);
const statusFilter = ref<StatusFilter>("all");
const priorityFilter = ref("all");
const searchQuery = ref("");
const viewMode = ref<"list" | "compact">("list");
const completingIds = ref(new Set<string>());
const undoTaskId = ref<string | null>(null);
const collapsed = reactive<Record<string, boolean>>({
  today: false,
  tomorrow: true,
  thisWeek: true,
  waiting: true,
  noDate: true,
  completed: true
});
let undoTimer: number | undefined;

watch(
  () => route.query.create,
  (value) => {
    if (value === "1") requestAnimationFrame(() => { if (createDrawer.value) createDrawer.value.open = true; });
  },
  { immediate: true }
);

watch(
  [() => route.query.record, () => crmStore.tasks.value],
  ([recordId]) => {
    if (typeof recordId !== "string") return;
    const task = crmStore.tasks.value.find((item) => item.id === recordId);
    if (task) {
      selectedTask.value = task;
      isTaskCrudOpen.value = true;
    }
  },
  { immediate: true }
);

onMounted(() => void crmStore.refreshActivities().catch(() => undefined));
onBeforeUnmount(() => window.clearTimeout(undoTimer));

const now = computed(() => new Date());
const startOfToday = computed(() => new Date(now.value.getFullYear(), now.value.getMonth(), now.value.getDate()));

function taskDate(task: Task) {
  return task.due_at ? new Date(task.due_at) : null;
}

function dayOffset(task: Task) {
  const due = taskDate(task);
  if (!due) return null;
  const day = new Date(due.getFullYear(), due.getMonth(), due.getDate()).getTime();
  return Math.round((day - startOfToday.value.getTime()) / 86400000);
}

function isCompleted(task: Task) {
  return Boolean(task.done_at || task.status === "completed");
}

function isOverdue(task: Task) {
  return !isCompleted(task) && Boolean(task.due_at && new Date(task.due_at).getTime() < Date.now());
}

function isWaiting(task: Task) {
  return !isCompleted(task) && task.status === "waiting";
}

function companyName(companyId: string) {
  return crmStore.companies.value.find((company) => company.id === companyId)?.name ?? "Компания";
}

function dealName(dealId: string | null) {
  return crmStore.deals.value.find((deal) => deal.id === dealId)?.title ?? "Без сделки";
}

function priorityTone(priority: string) {
  if (priority === "high" || priority === "urgent") return "high";
  if (priority === "low") return "low";
  return "medium";
}

function priorityLabel(priority: string) {
  const tone = priorityTone(priority);
  return tone === "high" ? "Высокий" : tone === "low" ? "Низкий" : "Средний";
}

function dueLabel(task: Task) {
  if (!task.due_at) return "Без срока";
  const due = new Date(task.due_at);
  const offset = dayOffset(task);
  const time = due.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  if (offset === 0) return time;
  if (offset === 1) return `Завтра, ${time}`;
  return due.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}

function ownerInitials() {
  const name = crmStore.me.value?.full_name ?? "Voknap User";
  return name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

const allTasks = computed(() => crmStore.tasks.value);
const openTasks = computed(() => allTasks.value.filter((task) => !isCompleted(task)));
const completedToday = computed(() => allTasks.value.filter((task) => {
  if (!task.done_at) return false;
  const done = new Date(task.done_at);
  return done.toDateString() === now.value.toDateString();
}));

const stats = computed(() => [
  { code: "today", icon: "▣", label: "Сегодня", value: openTasks.value.filter((task) => dayOffset(task) === 0).length },
  { code: "overdue", icon: "⌑", label: "Просрочено", value: openTasks.value.filter(isOverdue).length },
  { code: "week", icon: "□", label: "На этой неделе", value: openTasks.value.filter((task) => { const offset = dayOffset(task); return offset !== null && offset >= 0 && offset <= 7; }).length },
  { code: "waiting", icon: "◷", label: "Ожидают", value: openTasks.value.filter(isWaiting).length },
  { code: "no-date", icon: "▤", label: "Без срока", value: openTasks.value.filter((task) => !task.due_at).length },
  { code: "done", icon: "✓", label: "Завершено сегодня", value: completedToday.value.length }
]);

const filteredTasks = computed(() => {
  const needle = searchQuery.value.trim().toLowerCase();
  return allTasks.value.filter((task) => {
    if (statusFilter.value === "open" && isCompleted(task)) return false;
    if (statusFilter.value === "overdue" && !isOverdue(task)) return false;
    if (statusFilter.value === "completed" && !isCompleted(task)) return false;
    if (priorityFilter.value !== "all" && priorityTone(task.priority) !== priorityFilter.value) return false;
    if (!needle) return true;
    return [task.title, task.description, companyName(task.company_id), dealName(task.deal_id)]
      .some((value) => String(value ?? "").toLowerCase().includes(needle));
  });
});

const groups = computed<TaskGroup[]>(() => {
  const tasks = filteredTasks.value;
  const open = tasks.filter((task) => !isCompleted(task));
  const completed = tasks.filter(isCompleted);
  const rows: TaskGroup[] = [
    { code: "today", title: "Сегодня", items: open.filter((task) => !isWaiting(task) && dayOffset(task) === 0) },
    { code: "tomorrow", title: "Завтра", items: open.filter((task) => !isWaiting(task) && dayOffset(task) === 1) },
    { code: "thisWeek", title: "На этой неделе", items: open.filter((task) => { const offset = dayOffset(task); return !isWaiting(task) && offset !== null && offset >= 2 && offset <= 7; }) },
    { code: "waiting", title: "Ожидают", items: open.filter(isWaiting) },
    { code: "noDate", title: "Без срока", items: open.filter((task) => !isWaiting(task) && (!task.due_at || isOverdue(task) || (dayOffset(task) ?? 0) > 7)) }
  ];
  if (statusFilter.value === "completed" || (statusFilter.value === "all" && completed.length)) {
    rows.push({ code: "completed", title: "Завершенные", items: completed });
  }
  return rows;
});

const aiFocus = computed(() => openTasks.value
  .map((task) => {
    const priority = priorityTone(task.priority);
    const score = (isOverdue(task) ? 100 : 0) + (priority === "high" ? 35 : priority === "medium" ? 15 : 0) + (dayOffset(task) === 0 ? 25 : 0);
    const reason = isOverdue(task)
      ? "Срок уже прошел. Лучше закрыть задачу первой."
      : priority === "high"
        ? "Высокий приоритет требует внимания сегодня."
        : dayOffset(task) === 0
          ? "Задача запланирована на сегодня."
          : "Связана с активной работой по клиенту.";
    return { task, score, reason };
  })
  .sort((a, b) => b.score - a.score)
  .slice(0, 3));

const calendarTasks = computed(() => openTasks.value
  .filter((task) => task.due_at && (dayOffset(task) === 0 || dayOffset(task) === 1))
  .sort((a, b) => new Date(a.due_at!).getTime() - new Date(b.due_at!).getTime())
  .slice(0, 4));

const recentActivity = computed(() => crmStore.activities.value.slice(0, 3));

async function completeTask(task: Task) {
  if (completingIds.value.has(task.id)) return;
  completingIds.value = new Set(completingIds.value).add(task.id);
  await new Promise((resolve) => window.setTimeout(resolve, 280));
  await crmStore.toggleTask(task);
  const next = new Set(completingIds.value);
  next.delete(task.id);
  completingIds.value = next;
  undoTaskId.value = task.id;
  window.clearTimeout(undoTimer);
  undoTimer = window.setTimeout(() => { undoTaskId.value = null; }, 5000);
}

async function undoComplete() {
  const task = crmStore.tasks.value.find((item) => item.id === undoTaskId.value);
  undoTaskId.value = null;
  window.clearTimeout(undoTimer);
  if (task?.done_at) await crmStore.toggleTask(task);
}

function openCompany(task: Task) {
  void router.push(`/companies/${task.company_id}`);
}

function openDeal(task: Task) {
  if (task.deal_id) void router.push({ path: "/deals", query: { deal: task.deal_id } });
}

function closeCreateDrawer() {
  if (createDrawer.value) createDrawer.value.open = false;
  if (route.query.create) void router.replace({ query: { ...route.query, create: undefined } });
}

function closeTaskCrud() {
  isTaskCrudOpen.value = false;
  if (route.query.record) void router.replace({ query: { ...route.query, record: undefined } });
}

function refreshActivities() {
  void crmStore.refreshActivities().catch(() => undefined);
}
</script>

<template>
  <section class="tasks-page">
    <section class="tasks-kpi-strip" aria-label="Сводка задач">
      <article v-for="item in stats" :key="item.code" class="tasks-kpi" :class="`is-${item.code}`">
        <span class="tasks-kpi__icon" aria-hidden="true">{{ item.icon }}</span>
        <span><small>{{ item.label }}</small><strong>{{ item.value }}</strong></span>
      </article>
    </section>

    <section class="tasks-toolbar" aria-label="Управление задачами">
      <div class="tasks-segmented" role="tablist" aria-label="Статус">
        <button v-for="option in [{ value: 'all', label: 'Все' }, { value: 'open', label: 'Открытые' }, { value: 'overdue', label: 'Просроченные' }, { value: 'completed', label: 'Завершенные' }]" :key="option.value" type="button" :class="{ active: statusFilter === option.value }" @click="statusFilter = option.value as StatusFilter">{{ option.label }}</button>
      </div>
      <label class="tasks-search">
        <span aria-hidden="true">⌕</span>
        <input v-model="searchQuery" type="search" placeholder="Поиск задач..." aria-label="Поиск задач" />
      </label>
      <select v-model="priorityFilter" class="tasks-select" aria-label="Приоритет">
        <option value="all">Любой приоритет</option>
        <option value="high">Высокий</option>
        <option value="medium">Средний</option>
        <option value="low">Низкий</option>
      </select>
      <div class="tasks-view-toggle" aria-label="Вид списка">
        <button type="button" :class="{ active: viewMode === 'list' }" aria-label="Подробный список" @click="viewMode = 'list'">☷</button>
        <button type="button" :class="{ active: viewMode === 'compact' }" aria-label="Компактный список" @click="viewMode = 'compact'">▦</button>
      </div>
    </section>

    <section class="tasks-shell">
      <main class="tasks-main">
        <section v-if="aiFocus.length" class="tasks-ai-focus">
          <header><div><span class="ai-spark" aria-hidden="true">✦</span><h2>Фокус AI</h2><small>Рекомендуем</small></div></header>
          <article v-for="(item, index) in aiFocus" :key="item.task.id" class="tasks-ai-row">
            <span class="ai-rank">{{ index + 1 }}</span>
            <button type="button" class="task-copy" @click="selectedTask = item.task">
              <strong>{{ item.task.title }}</strong><small>{{ item.reason }}</small>
            </button>
            <span class="tasks-priority" :class="`is-${priorityTone(item.task.priority)}`">↑ {{ priorityLabel(item.task.priority) }}</span>
            <button type="button" class="task-company" @click="openCompany(item.task)">▥ {{ companyName(item.task.company_id) }}</button>
            <button type="button" class="tasks-open" @click="selectedTask = item.task">Открыть</button>
          </article>
        </section>

        <section class="tasks-group-stack" :class="{ compact: viewMode === 'compact' }">
          <section v-for="group in groups" :key="group.code" class="tasks-group">
            <button type="button" class="tasks-group__header" :aria-expanded="!collapsed[group.code]" @click="collapsed[group.code] = !collapsed[group.code]">
              <span><strong>{{ group.title }}</strong><small>{{ group.items.length }}</small></span><span class="group-chevron">⌄</span>
            </button>
            <div v-show="!collapsed[group.code]" class="tasks-group__content">
              <article v-for="task in group.items" :key="task.id" class="tasks-row" :class="{ leaving: completingIds.has(task.id), completed: isCompleted(task) }">
                <button type="button" class="tasks-check" :class="{ checked: isCompleted(task) }" :aria-label="isCompleted(task) ? 'Вернуть задачу' : 'Завершить задачу'" @click="isCompleted(task) ? crmStore.toggleTask(task) : completeTask(task)"><span>✓</span></button>
                <button type="button" class="task-copy" @click="selectedTask = task">
                  <strong>{{ task.title }}</strong><small>{{ task.description || "Без описания" }}</small>
                </button>
                <span class="tasks-priority" :class="`is-${priorityTone(task.priority)}`">↑ {{ priorityLabel(task.priority) }}</span>
                <span class="task-due" :class="{ overdue: isOverdue(task) }">◷ {{ dueLabel(task) }}</span>
                <button type="button" class="task-company" @click="openCompany(task)">▥ {{ companyName(task.company_id) }}</button>
                <button type="button" class="task-deal" :disabled="!task.deal_id" @click="openDeal(task)">{{ dealName(task.deal_id) }}</button>
                <span class="task-owner"><i>{{ ownerInitials() }}</i><span>{{ crmStore.me.value?.full_name ?? "Владелец" }}</span></span>
                <button type="button" class="task-menu" aria-label="Действия с задачей" @click="selectedTask = task">⋮</button>
              </article>
              <div v-if="!group.items.length" class="tasks-empty"><strong>Задач нет</strong><span>Новые задачи появятся здесь автоматически.</span></div>
            </div>
          </section>
        </section>
      </main>

      <aside class="tasks-right-rail">
        <section class="tasks-rail-card">
          <header><h2>AI рекомендации</h2><button type="button" @click="statusFilter = 'open'">Смотреть все</button></header>
          <div class="rail-list">
            <article><span class="rail-icon purple">✉</span><div><strong>Повторный контакт</strong><small>Проверьте задачи без ответа</small></div><b>{{ openTasks.filter((task) => /ответ|письм|follow/i.test(`${task.title} ${task.description}`)).length }}</b></article>
            <article><span class="rail-icon orange">◷</span><div><strong>Задачи на сегодня</strong><small>Срок наступает сегодня</small></div><b>{{ stats[0].value }}</b></article>
            <article><span class="rail-icon green">↗</span><div><strong>Высокий приоритет</strong><small>Требуют внимания</small></div><b>{{ openTasks.filter((task) => priorityTone(task.priority) === 'high').length }}</b></article>
          </div>
        </section>

        <section class="tasks-rail-card">
          <header><h2>Календарь</h2><button type="button" @click="statusFilter = 'open'">Смотреть все</button></header>
          <div v-if="calendarTasks.length" class="calendar-list">
            <button v-for="task in calendarTasks" :key="task.id" type="button" @click="selectedTask = task"><time>{{ task.due_at ? new Date(task.due_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '' }}</time><span>{{ task.title }}</span></button>
          </div>
          <p v-else class="rail-empty">Событий на сегодня и завтра нет</p>
        </section>

        <section class="tasks-rail-card">
          <header><h2>Последняя активность</h2><button type="button" @click="refreshActivities">Обновить</button></header>
          <div v-if="recentActivity.length" class="activity-list">
            <article v-for="activity in recentActivity" :key="activity.id"><span>{{ ownerInitials() }}</span><div><small>{{ activity.type }}</small><strong>{{ activity.title }}</strong><time>{{ new Date(activity.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) }}</time></div></article>
          </div>
          <p v-else class="rail-empty">Активность появится после первого действия</p>
        </section>
      </aside>
    </section>

    <details ref="createDrawer" class="tasks-create-drawer">
      <summary>Новая задача</summary>
      <div class="drawer-head"><div><small>Рабочий процесс</small><h2>Новая задача</h2></div><button type="button" aria-label="Закрыть" @click="closeCreateDrawer">×</button></div>
      <form class="tasks-create-form" @submit.prevent="crmStore.createTask().then(closeCreateDrawer)">
        <label><span>Компания</span><select v-model="crmStore.taskForm.value.company_id" required><option value="">Выбрать</option><option v-for="company in crmStore.companies.value" :key="company.id" :value="company.id">{{ company.name }}</option></select></label>
        <label><span>Название</span><input v-model="crmStore.taskForm.value.title" required /></label>
        <label><span>Описание</span><textarea v-model="crmStore.taskForm.value.description" rows="4"></textarea></label>
        <label><span>Сделка</span><select v-model="crmStore.taskForm.value.deal_id"><option value="">Без сделки</option><option v-for="deal in crmStore.deals.value.filter((item) => item.company_id === crmStore.taskForm.value.company_id)" :key="deal.id" :value="deal.id">{{ deal.title }}</option></select></label>
        <label><span>Приоритет</span><select v-model="crmStore.taskForm.value.priority"><option value="high">Высокий</option><option value="normal">Средний</option><option value="low">Низкий</option></select></label>
        <label><span>Срок</span><input v-model="crmStore.taskForm.value.due_at" type="datetime-local" /></label>
        <button type="submit" :disabled="crmStore.isLoading.value">Создать задачу</button>
      </form>
    </details>
    <div v-if="createDrawer?.open" class="tasks-drawer-backdrop" @click="closeCreateDrawer"></div>

    <aside v-if="selectedTask" class="task-details" aria-label="Детали задачи">
      <header><div><small>Задача</small><h2>{{ selectedTask.title }}</h2></div><button type="button" aria-label="Закрыть" @click="selectedTask = null">×</button></header>
      <p>{{ selectedTask.description || "Описание не добавлено." }}</p>
      <dl><div><dt>Компания</dt><dd><button type="button" @click="openCompany(selectedTask)">{{ companyName(selectedTask.company_id) }}</button></dd></div><div><dt>Сделка</dt><dd>{{ dealName(selectedTask.deal_id) }}</dd></div><div><dt>Срок</dt><dd>{{ dueLabel(selectedTask) }}</dd></div><div><dt>Приоритет</dt><dd><span class="tasks-priority" :class="`is-${priorityTone(selectedTask.priority)}`">{{ priorityLabel(selectedTask.priority) }}</span></dd></div></dl>
      <button class="secondary" type="button" @click="isTaskCrudOpen = true">Редактировать · история · lifecycle</button>
      <button v-if="!isCompleted(selectedTask)" type="button" class="details-primary" @click="completeTask(selectedTask); selectedTask = null">Завершить задачу</button>
    </aside>
    <div v-if="selectedTask" class="tasks-drawer-backdrop" @click="selectedTask = null"></div>

    <EntityCrudDrawer v-if="isTaskCrudOpen && selectedTask" entity-type="tasks" :record="selectedTask" @saved="selectedTask = $event as Task" @close="closeTaskCrud" @removed="selectedTask = null; closeTaskCrud()" />

    <div v-if="undoTaskId" class="tasks-toast" role="status"><span>Задача завершена</span><button type="button" @click="undoComplete">Отменить</button></div>
  </section>
</template>

<style scoped>
.tasks-page { --t-bg:#f6f8fb; --t-surface:#fff; --t-soft:#fafbfc; --t-border:#e4e9f0; --t-border-strong:#d8e0ea; --t-text:#172033; --t-secondary:#566174; --t-muted:#7b8798; --t-primary:#0b72e7; --t-primary-soft:#edf5ff; --t-purple:#7656e8; --t-purple-soft:#f3efff; min-width:0; color:var(--t-text); }
.tasks-page *, .tasks-page *::before, .tasks-page *::after { box-sizing:border-box; min-width:0; }
.tasks-page button { min-height:0; border-radius:8px; box-shadow:none; }
.tasks-kpi-strip { display:grid; grid-template-columns:repeat(6,minmax(118px,1fr)); gap:12px; margin-bottom:18px; }
.tasks-kpi { display:grid; grid-template-columns:36px minmax(0,1fr); gap:10px; align-items:center; min-height:74px; padding:12px 13px; border:1px solid var(--t-border); border-radius:12px; background:var(--t-surface); box-shadow:0 2px 8px rgb(15 23 42 / 4%); }
.tasks-kpi__icon { display:grid; place-items:center; width:36px; height:36px; border-radius:10px; color:var(--t-primary); background:var(--t-primary-soft); font-weight:800; }
.tasks-kpi.is-overdue .tasks-kpi__icon { color:#ef4444; background:#fff0f0; }.tasks-kpi.is-waiting .tasks-kpi__icon { color:#d77b00; background:#fff7e6; }.tasks-kpi.is-done .tasks-kpi__icon { color:#16a36a; background:#eaf8f1; }.tasks-kpi.is-week .tasks-kpi__icon { color:var(--t-purple); background:var(--t-purple-soft); }
.tasks-kpi small,.tasks-kpi strong { display:block; }.tasks-kpi small { overflow:hidden; color:var(--t-muted); font-size:10px; line-height:14px; white-space:nowrap; text-overflow:ellipsis; }.tasks-kpi strong { margin-top:1px; font-size:18px; line-height:24px; }
.tasks-toolbar { display:grid; grid-template-columns:auto minmax(180px,1fr) 180px auto; gap:10px; align-items:center; margin-bottom:16px; }
.tasks-segmented { display:flex; gap:7px; }.tasks-segmented button,.tasks-view-toggle button { height:38px; border:1px solid var(--t-border-strong); padding:0 14px; color:var(--t-secondary); background:#fff; font-size:12px; font-weight: 600; white-space:nowrap; }.tasks-segmented button.active { border-color:var(--t-primary); color:#fff; background:var(--t-primary); }
.tasks-search { position:relative; display:block; }.tasks-search span { position:absolute; top:50%; left:12px; z-index:1; color:var(--t-muted); transform:translateY(-50%); }.tasks-search input,.tasks-select { width:100%; height:38px; border:1px solid var(--t-border-strong); border-radius:8px; outline:0; color:var(--t-text); background:#fff; font-size:12px; }.tasks-search input { padding:0 12px 0 35px; }.tasks-select { padding:0 9px; }.tasks-search input:focus,.tasks-select:focus { border-color:var(--t-primary); box-shadow:0 0 0 3px rgb(11 114 231 / 10%); }
.tasks-view-toggle { display:flex; }.tasks-view-toggle button { width:42px; padding:0; border-radius:0; }.tasks-view-toggle button:first-child { border-radius:8px 0 0 8px; }.tasks-view-toggle button:last-child { margin-left:-1px; border-radius:0 8px 8px 0; }.tasks-view-toggle button.active { z-index:1; border-color:#9bc8ff; color:var(--t-primary); background:#f5f9ff; }
.tasks-shell { display:grid; grid-template-columns:minmax(0,1fr) 300px; gap:20px; align-items:start; }.tasks-main { min-width:0; }.tasks-ai-focus { overflow:hidden; margin-bottom:16px; border:1px solid #e7e1ff; border-radius:12px; background:linear-gradient(180deg,#fbfaff,#f8f6ff); box-shadow:0 2px 8px rgb(83 56 163 / 4%); }.tasks-ai-focus > header { display:flex; align-items:center; min-height:44px; padding:0 14px; border-bottom:1px solid #ece7ff; }.tasks-ai-focus > header div { display:flex; align-items:center; gap:8px; }.tasks-ai-focus h2 { margin:0; font-size:13px; }.tasks-ai-focus header small { padding:3px 8px; border-radius:99px; color:var(--t-purple); background:var(--t-purple-soft); font-size:10px; }.ai-spark { color:var(--t-purple); }
.tasks-ai-row { display:grid; grid-template-columns:28px minmax(180px,1fr) auto minmax(92px,125px) auto; gap:11px; align-items:center; min-height:68px; padding:9px 12px; border-bottom:1px solid #ece7ff; }.tasks-ai-row:last-child { border-bottom:0; }.ai-rank { display:grid; place-items:center; width:26px; height:26px; border-radius:50%; color:var(--t-purple); background:var(--t-purple-soft); font-size:11px; font-weight: 700; }
.task-copy,.task-company,.task-deal,.tasks-open,.task-menu,.tasks-check,.tasks-group__header,.tasks-rail-card header button,.calendar-list button,.task-details dd button { border:0; color:inherit; background:transparent; text-align:left; }.task-copy { display:block; overflow:hidden; width:100%; padding:0; }.task-copy strong,.task-copy small { display:block; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }.task-copy strong { font-size:12px; line-height:17px; }.task-copy small { margin-top:2px; color:var(--t-muted); font-size:10px; line-height:15px; font-weight:400; }
.tasks-priority { display:inline-flex; align-items:center; width:fit-content; height:22px; padding:0 8px; border-radius:99px; font-size:10px; font-weight:700; white-space:nowrap; }.tasks-priority.is-high { color:#ef4444; background:#fff0f0; }.tasks-priority.is-medium { color:#d77b00; background:#fff7e6; }.tasks-priority.is-low { color:#16a36a; background:#eaf8f1; }
.task-company,.task-deal { overflow:hidden; padding:4px 0; color:var(--t-secondary); font-size:10px; white-space:nowrap; text-overflow:ellipsis; }.task-company:hover,.task-deal:not(:disabled):hover { color:var(--t-primary); }.task-deal:disabled { opacity:.62; cursor:default; }.tasks-open { height:30px; border:1px solid var(--t-border-strong); padding:0 11px; color:var(--t-text); background:#fff; font-size:10px; font-weight:700; }.tasks-open:hover { border-color:#b9c6d6; background:#f8fafc; }
.tasks-group-stack { display:grid; gap:10px; }.tasks-group { overflow:hidden; border:1px solid var(--t-border); border-radius:12px; background:#fff; box-shadow:0 1px 3px rgb(15 23 42 / 2%); }.tasks-group__header { display:flex; align-items:center; justify-content:space-between; width:100%; min-height:44px; padding:0 14px; }.tasks-group__header > span:first-child { display:flex; align-items:center; gap:8px; }.tasks-group__header strong { font-size:13px; }.tasks-group__header small { display:grid; place-items:center; min-width:22px; height:22px; border-radius:99px; padding:0 6px; color:var(--t-primary); background:var(--t-primary-soft); font-size:10px; font-weight:700; }.group-chevron { color:var(--t-secondary); transition:transform 150ms ease; }.tasks-group__header[aria-expanded="false"] .group-chevron { transform:rotate(-90deg); }
.tasks-row { display:grid; grid-template-columns:20px minmax(180px,1fr) auto 74px minmax(90px,125px) minmax(90px,125px) minmax(100px,142px) 30px; gap:10px; align-items:center; min-height:56px; padding:8px 12px; border-top:1px solid #edf0f4; background:#fff; transition:opacity 280ms ease,transform 280ms ease,background 120ms ease; }.tasks-row:hover { background:#fafbfd; }.tasks-row.leaving { opacity:0; transform:translateX(14px); }.tasks-row.completed .task-copy strong,.tasks-row.completed .task-copy small { color:#919aa8; text-decoration:line-through; }.tasks-check { display:grid; place-items:center; width:18px; height:18px; border:1.5px solid #cad3df; border-radius:50%; padding:0; }.tasks-check span { opacity:0; color:#fff; font-size:10px; }.tasks-check:hover { border-color:var(--t-primary); }.tasks-check.checked { border-color:var(--t-primary); background:var(--t-primary); }.tasks-check.checked span { opacity:1; }.task-due { color:var(--t-secondary); font-size:10px; white-space:nowrap; }.task-due.overdue { color:#ef4444; }.task-owner { display:flex; align-items:center; gap:7px; overflow:hidden; color:var(--t-secondary); font-size:10px; }.task-owner i { display:grid; flex:0 0 26px; place-items:center; width:26px; height:26px; border-radius:50%; color:#fff; background:#7656a8; font-size:9px; font-style:normal; font-weight:700; }.task-owner span { overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }.task-menu { display:grid; place-items:center; width:30px; height:30px; border:1px solid var(--t-border-strong); color:var(--t-muted); background:#fff; font-size:17px; }.task-menu:hover { color:var(--t-text); background:#f8fafc; }.tasks-group-stack.compact .tasks-row { min-height:46px; padding-top:5px; padding-bottom:5px; }.tasks-group-stack.compact .task-copy small,.tasks-group-stack.compact .task-deal { display:none; }.tasks-group-stack.compact .tasks-row { grid-template-columns:20px minmax(180px,1fr) auto 74px minmax(90px,125px) minmax(100px,142px) 30px; }
.tasks-empty { display:grid; justify-items:center; gap:3px; padding:24px; border-top:1px solid #edf0f4; color:var(--t-muted); font-size:11px; }.tasks-empty strong { color:var(--t-secondary); font-size:12px; }
.tasks-right-rail { position:sticky; top:94px; display:grid; gap:16px; max-height:calc(100dvh - 112px); overflow:auto; scrollbar-width:thin; }.tasks-rail-card { padding:15px; border:1px solid var(--t-border); border-radius:12px; background:#fff; box-shadow:0 2px 8px rgb(15 23 42 / 4%); }.tasks-rail-card > header { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:14px; }.tasks-rail-card h2 { margin:0; font-size:13px; }.tasks-rail-card header button { padding:0; color:var(--t-primary); font-size:10px; }.rail-list { display:grid; gap:14px; }.rail-list article { display:grid; grid-template-columns:32px minmax(0,1fr) auto; gap:9px; align-items:center; }.rail-icon { display:grid; place-items:center; width:32px; height:32px; border-radius:10px; color:var(--t-primary); background:var(--t-primary-soft); }.rail-icon.purple { color:var(--t-purple); background:var(--t-purple-soft); }.rail-icon.orange { color:#f08a13; background:#fff3e8; }.rail-icon.green { color:#16a36a; background:#eaf8f1; }.rail-list strong,.rail-list small { display:block; }.rail-list strong { font-size:11px; line-height:16px; }.rail-list small { overflow:hidden; margin-top:1px; color:var(--t-muted); font-size:10px; line-height:14px; white-space:nowrap; text-overflow:ellipsis; }.rail-list b { display:grid; place-items:center; min-width:24px; height:24px; border-radius:99px; padding:0 6px; color:var(--t-primary); background:var(--t-primary-soft); font-size:10px; }
.calendar-list { display:grid; gap:2px; }.calendar-list button { display:grid; grid-template-columns:48px minmax(0,1fr); gap:8px; width:100%; padding:8px 0; }.calendar-list time { color:var(--t-text); font-size:12px; font-weight:700; }.calendar-list span { overflow:hidden; color:var(--t-secondary); font-size:10px; white-space:nowrap; text-overflow:ellipsis; }.activity-list { display:grid; gap:13px; }.activity-list article { display:grid; grid-template-columns:24px minmax(0,1fr); gap:8px; }.activity-list article > span { display:grid; place-items:center; width:24px; height:24px; border-radius:50%; color:#fff; background:#8b6c61; font-size:8px; font-weight:700; }.activity-list div { display:grid; gap:1px; }.activity-list small { color:var(--t-muted); font-size:9px; text-transform:capitalize; }.activity-list strong { overflow:hidden; font-size:10px; line-height:15px; white-space:nowrap; text-overflow:ellipsis; }.activity-list time { color:var(--t-muted); font-size:9px; }.rail-empty { margin:0; color:var(--t-muted); font-size:10px; line-height:16px; }
.tasks-create-drawer,.task-details { position:fixed; top:0; right:0; z-index:51; width:min(420px,100vw); height:100dvh; overflow:auto; border:0; border-left:1px solid var(--t-border); padding:22px; background:#fff; box-shadow:-18px 0 50px rgb(15 23 42 / 15%); }.tasks-create-drawer:not([open]) { display:none; }.tasks-create-drawer > summary { display:none; }.drawer-head,.task-details > header { display:flex; align-items:flex-start; justify-content:space-between; gap:15px; margin-bottom:24px; }.drawer-head small,.task-details header small { color:var(--t-muted); font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.08em; }.drawer-head h2,.task-details h2 { margin:4px 0 0; font-size:22px; line-height:28px; }.drawer-head button,.task-details header button { width:34px; height:34px; border:1px solid var(--t-border); padding:0; color:var(--t-secondary); background:#fff; font-size:20px; }.tasks-create-form { display:grid; gap:15px; }.tasks-create-form label { display:grid; gap:6px; }.tasks-create-form label > span { color:var(--t-secondary); font-size:11px; font-weight: 600; }.tasks-create-form input,.tasks-create-form select,.tasks-create-form textarea { width:100%; border:1px solid var(--t-border-strong); border-radius:8px; padding:10px 11px; outline:0; color:var(--t-text); background:#fff; font:inherit; font-size:12px; }.tasks-create-form input,.tasks-create-form select { height:40px; padding-top:0; padding-bottom:0; }.tasks-create-form input:focus,.tasks-create-form select:focus,.tasks-create-form textarea:focus { border-color:var(--t-primary); box-shadow:0 0 0 3px rgb(11 114 231 / 10%); }.tasks-create-form > button,.details-primary { height:40px; margin-top:4px; border:0; color:#fff; background:var(--t-primary); font-size:12px; font-weight:700; }.tasks-drawer-backdrop { position:fixed; inset:0; z-index:50; background:rgb(17 24 39 / 28%); }.task-details p { margin:0 0 22px; color:var(--t-secondary); font-size:12px; line-height:19px; }.task-details dl { display:grid; gap:0; margin:0 0 24px; }.task-details dl div { display:grid; grid-template-columns:90px minmax(0,1fr); gap:12px; padding:12px 0; border-bottom:1px solid var(--t-border); }.task-details dt { color:var(--t-muted); font-size:11px; }.task-details dd { margin:0; color:var(--t-text); font-size:11px; font-weight: 600; }.task-details dd button { padding:0; color:var(--t-primary); }.details-primary { width:100%; }
.tasks-toast { position:fixed; right:24px; bottom:24px; z-index:70; display:flex; align-items:center; gap:18px; min-height:46px; border:1px solid #303a4b; border-radius:10px; padding:0 14px; color:#fff; background:#172033; box-shadow:0 14px 35px rgb(15 23 42 / 22%); font-size:12px; }.tasks-toast button { border:0; padding:6px; color:#8cc3ff; background:transparent; font-size:11px; font-weight: 700; }
/* Readability pass: larger type without changing component grid. */
.tasks-kpi small { font-size:11px; line-height:15px; }
.tasks-kpi strong { font-size:20px; line-height:25px; }
.tasks-segmented button,.tasks-search input,.tasks-select { font-size:13px; }
.tasks-ai-focus h2,.tasks-group__header strong,.tasks-rail-card h2 { font-size:14px; line-height:19px; }
.tasks-ai-focus header small,.tasks-group__header small,.ai-rank { font-size:11px; }
.task-copy strong { font-size:13px; line-height:18px; }
.task-copy small { font-size:11px; line-height:16px; }
.tasks-priority,.task-due,.task-company,.task-deal,.task-owner,.tasks-open { font-size:11px; }
.tasks-row { min-height:60px; }
.tasks-ai-row { min-height:72px; }
.tasks-empty { font-size:12px; }.tasks-empty strong { font-size:13px; }
.tasks-rail-card header button { font-size:11px; }
.rail-list strong { font-size:12px; line-height:17px; }
.rail-list small { font-size:11px; line-height:15px; }
.rail-list b { font-size:11px; }
.calendar-list time { font-size:13px; }.calendar-list span { font-size:11px; }
.activity-list small,.activity-list time { font-size:10px; }.activity-list strong { font-size:11px; line-height:16px; }
.rail-empty { font-size:11px; line-height:17px; }
.tasks-create-form label > span,.task-details dt,.task-details dd { font-size:12px; }
.tasks-create-form input,.tasks-create-form select,.tasks-create-form textarea,.task-details p { font-size:13px; }
.tasks-toast { font-size:13px; }.tasks-toast button { font-size:12px; }
@media (max-width:1320px) { .tasks-kpi-strip { grid-template-columns:repeat(3,minmax(140px,1fr)); }.tasks-shell { grid-template-columns:minmax(0,1fr) 260px; }.tasks-row { grid-template-columns:20px minmax(170px,1fr) auto 70px minmax(90px,120px) minmax(100px,135px) 30px; }.task-deal { display:none; }.tasks-toolbar { grid-template-columns:1fr 1fr auto; }.tasks-segmented { grid-column:1/-1; } }
@media (max-width:1040px) { .tasks-shell { grid-template-columns:1fr; }.tasks-right-rail { position:static; grid-template-columns:repeat(2,minmax(0,1fr)); max-height:none; overflow:visible; }.tasks-right-rail .tasks-rail-card:last-child { grid-column:1/-1; }.tasks-ai-row { grid-template-columns:28px minmax(160px,1fr) auto auto; }.tasks-ai-row .task-company { display:none; } }
@media (max-width:720px) { .tasks-kpi-strip { grid-template-columns:repeat(2,minmax(125px,1fr)); }.tasks-toolbar { grid-template-columns:minmax(0,1fr) auto; }.tasks-segmented { grid-column:1/-1; overflow:auto; }.tasks-select { display:none; }.tasks-row,.tasks-group-stack.compact .tasks-row { grid-template-columns:20px minmax(0,1fr) 30px; }.tasks-row > :not(.tasks-check):not(.task-copy):not(.task-menu) { display:none; }.tasks-ai-row { grid-template-columns:28px minmax(0,1fr) auto; }.tasks-ai-row .tasks-priority { display:none; }.tasks-right-rail { grid-template-columns:1fr; }.tasks-right-rail .tasks-rail-card:last-child { grid-column:auto; }.tasks-create-drawer,.task-details { padding:18px; } }
</style>
