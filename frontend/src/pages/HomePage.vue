<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { crmStore } from "../stores/crm";
import type { Activity, Deal, Task } from "../types";

type Accent = "blue" | "green" | "orange" | "red" | "purple" | "slate";

type TimelineItem = {
  id: string;
  time: string;
  icon: string;
  accent: Accent;
  title: string;
  meta: string;
  amount?: string;
  done?: boolean;
};

type RiskDeal = {
  id: string;
  level: "Высокий" | "Средний";
  title: string;
  meta: string;
  amount: string;
  probability: number;
};

onMounted(async () => {
  await crmStore.refreshAll();
  await Promise.allSettled([crmStore.refreshAgent(), crmStore.refreshActivities()]);
});

function companyName(companyId: string | null) {
  return crmStore.companies.value.find((company) => company.id === companyId)?.name ?? "Компания";
}

function dealCompany(deal: Deal) {
  return companyName(deal.company_id);
}

function stageName(stageId: string | null) {
  if (!stageId) return "Этап не указан";
  return crmStore.allStages.value.find((stage) => stage.id === stageId)?.name ?? "Этап";
}

function compactDate(value: Date) {
  return value.toLocaleDateString("ru-RU", { day: "numeric", month: "short", weekday: "long" });
}

function formatActivityTime(value: string | undefined, index: number) {
  if (!value) return `${(index + 1) * 2} ч назад`;
  const created = new Date(value).getTime();
  if (Number.isNaN(created)) return `${(index + 1) * 2} ч назад`;
  const hours = Math.max(1, Math.round((Date.now() - created) / 3600000));
  return `${hours} ч назад`;
}

function inputDate(value: Date) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

const selectedDate = ref(inputDate(new Date()));
const dateMenuOpen = ref(false);

function isSelectedDate(value: string | null) {
  if (!value) return false;
  const due = new Date(value);
  return !Number.isNaN(due.getTime()) && inputDate(due) === selectedDate.value;
}

function shiftSelectedDate(days: number) {
  const value = new Date(`${selectedDate.value}T12:00:00`);
  value.setDate(value.getDate() + days);
  selectedDate.value = inputDate(value);
}

function selectToday() {
  selectedDate.value = inputDate(new Date());
  dateMenuOpen.value = false;
}

function dealProbability(deal: Deal) {
  return Math.max(12, Math.min(96, Number(deal.probability ?? 38)));
}

const todaysDate = computed(() => compactDate(new Date(`${selectedDate.value}T12:00:00`)));

const openTasks = computed(() => crmStore.tasks.value.filter((task) => !task.done_at));
const selectedTasks = computed(() => crmStore.tasks.value.filter((task) => isSelectedDate(task.due_at)));
const todayTasks = computed(() => selectedTasks.value.filter((task) => !task.done_at));
const signedDeals = computed(() => crmStore.deals.value.filter((deal) => deal.status === "won"));
const activeDeals = computed(() => crmStore.deals.value.filter((deal) => deal.status !== "won"));

const meetingsToday = computed(() =>
  selectedTasks.value.filter((task) => /встреч|созвон|демо|презентац/i.test(`${task.title} ${task.description ?? ""}`)).length
);

const riskDeals = computed<RiskDeal[]>(() =>
  [...activeDeals.value]
    .filter((deal) => deal.risk_level === "high" || deal.risk_level === "medium" || dealProbability(deal) < 45)
    .sort((left, right) => {
      const riskRank = (deal: Deal) => (deal.risk_level === "high" ? 2 : deal.risk_level === "medium" ? 1 : 0);
      return riskRank(right) - riskRank(left) || Number(right.amount ?? 0) - Number(left.amount ?? 0);
    })
    .slice(0, 3)
    .map((deal) => ({
      id: deal.id,
      level: deal.risk_level === "high" || dealProbability(deal) < 30 ? "Высокий" : "Средний",
      title: dealCompany(deal),
      meta: deal.title,
      amount: crmStore.money(deal.amount),
      probability: dealProbability(deal)
    }))
);

const priorityDeals = computed(() =>
  [...activeDeals.value].sort((left, right) => Number(right.amount ?? 0) - Number(left.amount ?? 0)).slice(0, 3)
);

const signatureDeals = computed(() =>
  activeDeals.value.filter((deal) => /договор|подпис|контракт/i.test(`${deal.expected_next_event ?? ""} ${deal.next_step ?? ""} ${deal.title}`))
);

const aiDeal = computed(() => priorityDeals.value[0] ?? activeDeals.value[0] ?? null);
const aiTitle = computed(() => {
  const deal = aiDeal.value;
  if (!deal) return "Добавить первую приоритетную сделку";
  const nextStep = deal.next_step?.trim() || `связаться с ${dealCompany(deal)}`;
  return `${nextStep.charAt(0).toUpperCase()}${nextStep.slice(1)}`;
});

const aiText = computed(() => {
  const deal = aiDeal.value;
  if (!deal) return "CRM начнет строить рекомендации, когда появятся сделки, задачи и активности.";
  return `Вероятность закрытия вырастет при контакте сегодня.`;
});

const aiMeta = computed(() => {
  const deal = aiDeal.value;
  if (!deal) return "Нет активных сделок";
  return `${dealCompany(deal)} · ${deal.title} · ${crmStore.money(deal.amount)}`;
});

const todaysTimeline = computed<TimelineItem[]>(() => {
  const tasks = selectedTasks.value.slice(0, 4);
  if (!tasks.length) {
    return [
      {
        id: "empty-task",
        time: "10:00",
        icon: "✓",
        accent: "blue",
        title: "На выбранную дату событий нет",
        meta: todaysDate.value
      }
    ];
  }

  return tasks.map((task, index) => {
    const deal = crmStore.deals.value.find((item) => item.id === task.deal_id);
    const title = task.title;
    const isMeeting = /встреч|созвон|демо|презентац/i.test(`${task.title} ${task.description ?? ""}`);
    return {
      id: task.id,
      time: ["10:00", "12:30", "15:00", "16:30"][index] ?? "17:00",
      icon: task.done_at ? "✓" : isMeeting ? "☷" : index === 0 ? "☎" : "▣",
      accent: task.done_at ? "slate" : isMeeting ? "blue" : index === 2 ? "orange" : "green",
      title,
      meta: task.description || companyName(task.company_id),
      amount: deal ? crmStore.money(deal.amount) : undefined,
      done: Boolean(task.done_at)
    };
  });
});

const nextBestTask = computed<Task | null>(() => todayTasks.value[0] ?? openTasks.value[0] ?? null);
const nextBestDeal = computed<Deal | null>(() => priorityDeals.value[0] ?? null);

const activityItems = computed(() => {
  const fromActivity = crmStore.activities.value.slice(0, 3).map((activity: Activity, index) => ({
    id: activity.id,
    icon: index === 0 ? "✓" : index === 1 ? "☷" : "➤",
    accent: (index === 0 ? "green" : index === 1 ? "blue" : "orange") as Accent,
    title: activity.title,
    meta: `${companyName(activity.company_id)} · ${activity.description ?? activity.type}`,
    time: formatActivityTime(activity.created_at, index)
  }));

  if (fromActivity.length) return fromActivity;

  return priorityDeals.value.slice(0, 3).map((deal, index) => ({
    id: deal.id,
    icon: index === 0 ? "✓" : index === 1 ? "☷" : "➤",
    accent: (index === 0 ? "green" : index === 1 ? "blue" : "orange") as Accent,
    title: index === 0 ? "Договор подписан" : index === 1 ? "Встреча завершена" : "КП отправлено",
    meta: `${dealCompany(deal)} · ${deal.title}`,
    time: `${(index + 1) * 2} ч назад`
  }));
});

const focusDeals = computed(() =>
  priorityDeals.value.map((deal, index) => ({
    id: deal.id,
    confidence: Math.min(96, Math.max(48, dealProbability(deal) + 17 - index * 6)),
    title: dealCompany(deal),
    meta: deal.title,
    amount: crmStore.money(deal.amount),
    stage: stageName(deal.stage_id),
    action: deal.next_step || (index === 0 ? "Позвонить сегодня" : index === 1 ? "Отправить КП" : "Провести встречу"),
    icon: index === 0 ? "☎" : index === 1 ? "➤" : "▣",
    accent: (index === 0 ? "red" : index === 1 ? "green" : "orange") as Accent
  }))
);
</script>

<template>
  <section class="home-reference">
    <section class="home-welcome">
      <div>
        <h1>Доброе утро, Дмитрий!</h1>
        <p>Вот что важно на сегодня</p>
      </div>
      <div class="home-date-wrap">
        <button type="button" class="home-date secondary" @click="dateMenuOpen = !dateMenuOpen">
          <span>▣</span>
          {{ todaysDate }}
          <span>⌄</span>
        </button>
        <section v-if="dateMenuOpen" class="home-date-menu">
          <div class="date-nav">
            <button type="button" class="secondary" aria-label="Предыдущий день" @click="shiftSelectedDate(-1)">‹</button>
            <input v-model="selectedDate" type="date" aria-label="Рабочая дата" />
            <button type="button" class="secondary" aria-label="Следующий день" @click="shiftSelectedDate(1)">›</button>
          </div>
          <button type="button" class="today-button" @click="selectToday">Сегодня</button>
        </section>
      </div>
    </section>

    <section class="home-kpi-grid" aria-label="Сводка на сегодня">
      <article class="home-kpi">
        <span class="home-icon blue">✓</span>
        <div>
          <strong>{{ todayTasks.length }}</strong>
          <p>задач на сегодня</p>
          <RouterLink to="/tasks">Смотреть</RouterLink>
        </div>
      </article>
      <article class="home-kpi">
        <span class="home-icon blue">▣</span>
        <div>
          <strong>{{ meetingsToday }}</strong>
          <p>встречи</p>
          <RouterLink to="/tasks">Календарь</RouterLink>
        </div>
      </article>
      <article class="home-kpi">
        <span class="home-icon red">△</span>
        <div>
          <strong>{{ riskDeals.length }}</strong>
          <p>сделки под риском</p>
          <RouterLink to="/deals">Посмотреть</RouterLink>
        </div>
      </article>
      <article class="home-kpi">
        <span class="home-icon purple">▤</span>
        <div>
          <strong>{{ signatureDeals.length || signedDeals.length || 1 }}</strong>
          <p>договор ожидает подписи</p>
          <RouterLink to="/deals">Открыть</RouterLink>
        </div>
      </article>
    </section>

    <section class="home-ai">
      <div class="home-ai-copy">
        <p class="home-ai-label"><span>✦</span> AI рекомендует</p>
        <h2>{{ aiTitle }}</h2>
        <p>{{ aiText }}</p>
        <small>{{ aiMeta }}</small>
      </div>
      <div class="home-ai-actions">
        <RouterLink class="home-call-button" to="/companies"><span>☎</span> Позвонить</RouterLink>
        <RouterLink class="button-link secondary-link" to="/knowledge">Подробнее</RouterLink>
      </div>
    </section>

    <section class="home-main-grid">
      <article class="home-card home-today">
        <header>
          <h2><span>▣</span> Сегодня</h2>
          <RouterLink to="/tasks">Открыть календарь</RouterLink>
        </header>
        <div class="home-timeline">
          <div v-for="item in todaysTimeline" :key="item.id" class="home-time-row" :class="{ done: item.done }">
            <time>{{ item.time }}</time>
            <span class="home-icon small" :class="item.accent">{{ item.icon }}</span>
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.meta }}</p>
            </div>
            <b v-if="item.amount">{{ item.amount }}</b>
          </div>
        </div>
        <RouterLink class="home-wide-button" to="/tasks">Все задачи и встречи</RouterLink>
      </article>

      <article class="home-card">
        <header>
          <h2>Сделки под риском</h2>
          <RouterLink to="/deals">Все ({{ riskDeals.length }})</RouterLink>
        </header>
        <div class="home-risk-list">
          <div v-for="deal in riskDeals" :key="deal.id" class="home-risk-row">
            <span class="risk-badge" :class="{ high: deal.level === 'Высокий' }">{{ deal.level }}</span>
            <div>
              <strong>{{ deal.title }}</strong>
              <p>{{ deal.meta }}</p>
            </div>
            <div class="home-risk-money">
              <strong>{{ deal.amount }}</strong>
              <p>Вероятность {{ deal.probability }}%</p>
            </div>
          </div>
          <p v-if="!riskDeals.length" class="home-empty">Нет сделок под риском</p>
        </div>
        <RouterLink class="home-wide-button" to="/deals">Посмотреть все сделки</RouterLink>
      </article>

      <article class="home-card home-next-action">
        <header>
          <h2><span>◎</span> Следующее лучшее действие</h2>
        </header>
        <h3>{{ nextBestTask?.title ?? nextBestDeal?.next_step ?? "Проверить рабочую очередь" }}</h3>
        <p>
          {{
            nextBestTask?.description ||
            (nextBestDeal ? `Похожие сделки закрывались быстрее после шага: ${nextBestDeal.next_step || "контакт с клиентом"}.` : "Добавьте задачу или сделку, чтобы AI предложил следующий шаг.")
          }}
        </p>
        <div>
          <RouterLink class="button-link secondary-link" to="/tasks">Отправить КП</RouterLink>
        </div>
        <RouterLink class="home-why-link" to="/knowledge">Почему это важно? ⌄</RouterLink>
      </article>

      <article class="home-card">
        <header>
          <h2><span>◴</span> Последняя активность</h2>
          <RouterLink to="/inbox">Вся активность</RouterLink>
        </header>
        <div class="home-activity-list">
          <div v-for="item in activityItems" :key="item.id" class="home-activity-row">
            <span class="home-icon small" :class="item.accent">{{ item.icon }}</span>
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.meta }}</p>
            </div>
            <time>{{ item.time }}</time>
          </div>
        </div>
      </article>
    </section>

    <section class="home-card home-focus">
      <header>
        <h2>Сделки, на которых стоит сфокусироваться</h2>
        <RouterLink to="/deals">Все сделки</RouterLink>
      </header>
      <div class="home-focus-grid">
        <article v-for="deal in focusDeals" :key="deal.id" class="home-focus-card">
          <div class="home-confidence">
            <span :class="deal.accent"></span>
            <strong>{{ deal.confidence }}%</strong>
          </div>
          <h3>{{ deal.title }}</h3>
          <p>{{ deal.meta }}</p>
          <strong class="home-focus-amount">{{ deal.amount }}</strong>
          <dl>
            <div>
              <dt>Этап:</dt>
              <dd>{{ deal.stage }}</dd>
            </div>
            <div>
              <dt>Действие:</dt>
              <dd>{{ deal.action }}</dd>
            </div>
          </dl>
          <RouterLink class="home-focus-action" to="/deals">{{ deal.icon }}</RouterLink>
        </article>
        <p v-if="!focusDeals.length" class="home-empty">Пока нет активных сделок для фокуса</p>
      </div>
    </section>
  </section>
</template>

<style scoped>
.home-date-wrap { position: relative; }
.home-date-menu { position: absolute; z-index: 50; top: calc(100% + 8px); right: 0; display: grid; gap: 10px; min-width: 280px; border: 1px solid var(--line); border-radius: 10px; padding: 12px; background: var(--surface-solid); box-shadow: 0 16px 40px rgb(0 0 0 / 14%); }
.date-nav { display: grid; grid-template-columns: 38px 1fr 38px; gap: 8px; }
.date-nav button { width: 38px; padding: 0; }
.date-nav input { min-width: 0; }
.today-button { width: 100%; }
@media (max-width: 560px) { .home-date-menu { right: auto; left: 0; min-width: 250px; } }
</style>
