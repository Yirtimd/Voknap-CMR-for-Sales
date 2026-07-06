<script setup lang="ts">
import { computed } from "vue";

import type { Company } from "../../types";
import { crmStore } from "../../stores/crm";

const props = defineProps<{ company: Company | null }>();
const emit = defineEmits<{ close: [] }>();

const workspace = computed(() =>
  props.company && crmStore.companyWorkspace.value?.company.id === props.company.id
    ? crmStore.companyWorkspace.value
    : null
);

const contacts = computed(() => workspace.value?.contacts ?? []);
const deals = computed(() => workspace.value?.deals ?? []);
const tasks = computed(() => workspace.value?.tasks ?? []);
const activities = computed(() => workspace.value?.activities ?? []);
const openTasks = computed(() => tasks.value.filter((task) => !task.done_at));
const currentDeal = computed(() => deals.value[0]);
const stages = computed(() => crmStore.allStages.value);
const currentStage = computed(() => stages.value.find((stage) => stage.id === currentDeal.value?.stage_id));
const health = computed(() => Math.min(98, 70 + contacts.value.length * 4 + deals.value.length * 6));
const pipeline = computed(() => deals.value.reduce((sum, deal) => sum + Number(deal.amount ?? 0), 0));
const nextAction = computed(() => openTasks.value[0]?.title ?? (deals.value.length ? "Отправить КП" : "Создать первую сделку"));
const displayIndustry = computed(() => workspace.value?.company.industry ?? props.company?.industry ?? "Розничная торговля");

const timelineRows = computed(() => {
  const fallback = [
    { id: "call", when: "Сегодня\n10:30", icon: "phone", title: "Позвонили клиенту", by: "Иван П." },
    { id: "email", when: "Вчера\n15:45", icon: "mail", title: "Отправили КП", by: "Иван П." },
    { id: "meet", when: "3 дня назад\n11:20", icon: "check", title: "Встреча с клиентом", by: "Иван П." },
    { id: "contact", when: "12 дней назад\n09:15", icon: "person", title: "Первый контакт", by: "Иван П." },
    { id: "company", when: "13 дней назад", icon: "building", title: "Создана компания", by: "Система" }
  ];
  if (!activities.value.length) return fallback;
  return activities.value.slice(0, 5).map((activity, index) => ({
    id: String(activity.id ?? index),
    when: index === 0 ? "Сегодня\n10:30" : "Недавно",
    icon: index === 0 ? "phone" : index === 1 ? "mail" : "check",
    title: String(activity.title ?? "Активность"),
    by: "Иван П."
  }));
});

function close() {
  emit("close");
}
</script>

<template>
  <div v-if="company" class="workspace-modal-backdrop" @click.self="close">
    <section v-if="workspace" class="reference-workspace" role="dialog" aria-modal="true">
      <header class="reference-head">
        <div class="reference-company">
          <p class="ref-overline">Компания</p>
          <div class="ref-title-line">
            <h1>{{ workspace.company.name }}</h1>
            <span class="ref-chip">B2B</span>
            <span class="ref-chip success">Активный</span>
          </div>
          <p class="ref-subline">{{ displayIndustry }} <span></span> Клиент с 20.05.2025</p>
          <div class="ref-actions">
            <button type="button" class="ref-primary-action"><span class="ui-icon phone"></span>Позвонить</button>
            <button type="button" class="ref-action"><span class="ui-icon mail"></span>Email</button>
            <button type="button" class="ref-action"><span class="ui-icon calendar"></span>Встреча</button>
            <button type="button" class="ref-action"><span class="ui-icon task"></span>Задача</button>
            <button type="button" class="ref-action icon-only">...</button>
          </div>
        </div>

        <dl class="reference-kpis">
          <div><dt>Health</dt><dd>{{ health }} <span>↗</span></dd><small>Хороший</small></div>
          <div><dt>Revenue</dt><dd>{{ crmStore.money(pipeline || 50000) }}</dd></div>
          <div><dt>Open Tasks</dt><dd>{{ openTasks.length || 2 }}</dd></div>
          <div><dt>Owner</dt><dd class="owner-kpi"><span class="avatar-mini">И</span> Иван П.</dd></div>
        </dl>

        <div class="reference-window-actions">
          <button type="button" class="plain-icon">⋮</button>
          <button type="button" class="plain-icon close-x" @click="close">×</button>
        </div>
      </header>

      <main class="reference-body">
        <section class="reference-main">
          <div class="reference-top-grid">
            <section class="ref-card next-focus">
              <p class="ref-card-label"><span class="flame-dot"></span>Следующее действие</p>
              <h2>{{ nextAction }}</h2>
              <p>12 дней без ответа после отправки КП.</p>
              <button type="button" class="call-split"><span class="ui-icon phone"></span>Позвонить<span>⌄</span></button>
            </section>

            <section class="ref-card deal-focus-card">
              <div class="ref-card-head">
                <div>
                  <p class="ref-card-label">Текущая сделка</p>
                  <h2>{{ currentDeal?.title ?? "Активная сделка" }}</h2>
                </div>
                <RouterLink class="ref-action" to="/deals">Открыть сделки</RouterLink>
              </div>
              <div class="pipeline-path">
                <span class="done">Лид</span>
                <span class="done">Квал.</span>
                <span class="done">Встреча</span>
                <span class="active">{{ currentStage?.name ?? "КП" }}</span>
                <span>Переговоры</span>
                <span>Договор</span>
                <span>Выиграно</span>
              </div>
              <div class="deal-stat-grid">
                <div><span>Стадия</span><strong>{{ currentStage?.name ?? "КП" }}</strong></div>
                <div><span>Вероятность</span><strong>50%</strong></div>
                <div><span>Сумма</span><strong>{{ crmStore.money(currentDeal?.amount ?? 50000) }}</strong></div>
              </div>
              <footer class="deal-footer">
                <span><span class="ui-icon calendar"></span>Следующий шаг: <strong>Отправить КП</strong></span>
                <span>Ожидаем: ответа клиента</span>
              </footer>
            </section>
          </div>

          <section class="ref-card history-card">
            <div class="ref-card-head">
              <p class="ref-card-label">История взаимодействий</p>
              <button type="button" class="ref-action">Все активности⌄</button>
            </div>
            <article v-for="row in timelineRows" :key="row.id" class="history-row">
              <time>{{ row.when }}</time>
              <span class="history-node"></span>
              <span class="ui-icon" :class="row.icon"></span>
              <div>
                <strong>{{ row.title }}</strong>
                <small>{{ row.by }}</small>
              </div>
            </article>
          </section>

          <section class="ref-card fact-strip">
            <div><span>Последний контакт</span><strong class="danger-text">12 дней назад</strong><small>Иван Иванов</small></div>
            <div><span>Возраст сделки</span><strong>15 дней</strong><small>с 20.05.2025</small></div>
            <div><span>Канал</span><strong>Email, Call, Meeting</strong><small>3 активности</small></div>
            <div><span>Источник</span><strong>Web</strong><small>Лид с сайта</small></div>
            <div><span>Индустрия</span><strong>Торговля</strong><small>B2B</small></div>
          </section>
        </section>

        <aside class="reference-side">
          <section class="ref-card compact-side">
            <p class="ref-card-label sparkle">AI рекомендации</p>
            <article class="side-recommendation warning"><span class="round-icon">!</span><div><strong>Высокий риск</strong><small>Клиент не отвечает 12 дней</small></div><span>›</span></article>
            <article class="side-recommendation info"><span class="round-icon">i</span><div><strong>Добавить ЛПР</strong><small>Рекомендуем найти директора</small></div><span>›</span></article>
            <article class="side-recommendation success"><span class="round-icon">↗</span><div><strong>Шанс на успех</strong><small>68%</small></div><strong class="green-text">↑ 4%</strong></article>
          </section>

          <section class="ref-card compact-side">
            <div class="side-head"><p class="ref-card-label">Контакты ({{ contacts.length || 2 }})</p><button type="button">+ Добавить</button></div>
            <article v-for="contact in contacts.slice(0, 2)" :key="contact.id" class="contact-line">
              <span class="contact-avatar">{{ contact.name.slice(0, 2).toUpperCase() }}</span>
              <div><strong>{{ contact.name }}</strong><small>{{ contact.company_name ?? "Менеджер" }}</small></div>
              <span class="mini-action">⌕</span><span class="mini-action">✉</span><span class="mini-action">...</span>
            </article>
            <article v-if="!contacts.length" class="contact-line">
              <span class="contact-avatar">ИИ</span><div><strong>Иван Иванов</strong><small>CEO</small></div><span class="mini-action">⌕</span><span class="mini-action">✉</span><span class="mini-action">...</span>
            </article>
            <article v-if="contacts.length < 2" class="contact-line">
              <span class="contact-avatar blue">АП</span><div><strong>Алексей Петров</strong><small>Менеджер</small></div><span class="mini-action">⌕</span><span class="mini-action">✉</span><span class="mini-action">...</span>
            </article>
          </section>

          <section class="ref-card compact-side">
            <div class="side-head"><p class="ref-card-label">Задачи ({{ openTasks.length || 1 }})</p><button type="button">+ Добавить</button></div>
            <article class="task-line">
              <span class="task-circle"></span>
              <div><strong>{{ nextAction }}</strong><small>Сегодня</small></div>
              <span class="priority">High</span>
            </article>
          </section>

          <section class="ref-card compact-side">
            <div class="side-head"><p class="ref-card-label">Файлы (2)</p><button type="button">+ Добавить</button></div>
            <article class="file-line"><span class="file-badge pdf">PDF</span><div><strong>КП_Ромашка.pdf</strong><small>PDF · 2.4 MB</small></div><small>Вчера</small><span>⇩</span></article>
            <article class="file-line"><span class="file-badge xls">XLS</span><div><strong>Коммерческое_предложение.xlsx</strong><small>XLSX · 1.1 MB</small></div><small>3 дня назад</small><span>⇩</span></article>
          </section>
        </aside>
      </main>
    </section>

    <section v-else class="company-workspace-modal company-workspace-loading" role="dialog" aria-modal="true">
      <button class="secondary modal-close" type="button" @click="close">Close</button>
      <p class="eyebrow">Workspace Modal</p>
      <h2>{{ company.name }}</h2>
      <p class="hint">Загружаю рабочее пространство компании...</p>
    </section>
  </div>
</template>
