<script setup lang="ts">
import { computed, ref } from "vue";

import { api, emptyToNull, post } from "../../api";
import type { Activity, CommunicationEvent, Company, CompanyFile, KnowledgeDocument, NextAction, Task } from "../../types";
import { crmStore } from "../../stores/crm";

const props = defineProps<{ company: Company | null }>();
const emit = defineEmits<{ close: [] }>();
const isSaving = ref(false);
const isNextActionEditorOpen = ref(false);
const nextActionForm = ref({ title: "", description: "", due_at: "", priority: "high" });
const drawerActionMode = ref<"call" | "email" | "meeting" | "task" | null>(null);
const callForm = ref({ subject: "Звонок клиенту", body: "", phone: "" });
const emailForm = ref({ subject: "Follow-up", body: "", recipient: "" });
const meetingActionForm = ref({ subject: "Встреча с клиентом", body: "", occurred_at: "" });
const drawerTaskForm = ref({ title: "Follow-up", description: "", due_at: "", priority: "high" });

const workspace = computed(() =>
  props.company && crmStore.companyWorkspace.value?.company.id === props.company.id
    ? crmStore.companyWorkspace.value
    : null
);

const contacts = computed(() => workspace.value?.contacts ?? []);
const deals = computed(() => workspace.value?.deals ?? []);
const tasks = computed(() => workspace.value?.tasks ?? []);
const activities = computed(() => workspace.value?.activities ?? []);
const files = computed(() => workspace.value?.files ?? []);
const knowledgeDocuments = computed(() => workspace.value?.knowledge_documents ?? []);
const openTasks = computed(() => tasks.value.filter((task) => !task.done_at));
const currentDeal = computed(() => deals.value[0]);
const stages = computed(() => crmStore.allStages.value);
const currentStage = computed(() => stages.value.find((stage) => stage.id === currentDeal.value?.stage_id));
const health = computed(() => workspace.value?.health.score ?? Math.min(98, 70 + contacts.value.length * 4 + deals.value.length * 6));
const healthTrend = computed(() => (workspace.value?.health.trend === "down" ? "↘" : workspace.value?.health.trend === "flat" ? "→" : "↗"));
const healthLabel = computed(() => workspace.value?.health.label ?? "Хороший");
const pipeline = computed(() => deals.value.reduce((sum, deal) => sum + Number(deal.amount ?? 0), 0));
const nextActionRecord = computed(() => workspace.value?.next_action ?? null);
const nextAction = computed(() => nextActionRecord.value?.title ?? currentDeal.value?.next_step ?? openTasks.value[0]?.title ?? (deals.value.length ? "Отправить КП" : "Создать первую сделку"));
const displayIndustry = computed(() => workspace.value?.company.industry ?? props.company?.industry ?? "Розничная торговля");
const companyType = computed(() => workspace.value?.company.company_type ?? displayIndustry.value ?? "B2B");
const clientSince = computed(() => workspace.value?.company.client_since ?? workspace.value?.company.created_at ?? props.company?.created_at);
const owner = computed(() => workspace.value?.company.owner);
const ownerName = computed(() => owner.value?.name ?? "Не назначен");
const ownerInitials = computed(() => owner.value?.initials ?? ownerName.value.slice(0, 1));
const lastContactAt = computed(() => workspace.value?.overview.last_contact_at ? relativeDate(String(workspace.value.overview.last_contact_at)) : "Нет контактов");
const lastContactPerson = computed(() => String(workspace.value?.overview.last_contact_person ?? "Не указан"));
const channelSummary = computed(() => String(workspace.value?.overview.channel_summary ?? "Нет каналов"));
const source = computed(() => workspace.value?.company.source ?? "Не указан");
const currentDealAge = computed(() => currentDeal.value?.age_days != null ? `${currentDeal.value.age_days} дней` : "Нет сделки");
const dealProbability = computed(() => currentDeal.value?.probability ?? null);
const expectedNextEvent = computed(() => currentDeal.value?.expected_next_event ?? "Ожидаем: следующего действия");
const recommendations = computed(() => workspace.value?.health.ai_recommendations ?? []);
const copilot = computed(() =>
  props.company && crmStore.companyCopilot.value?.company_id === props.company.id
    ? crmStore.companyCopilot.value
    : null
);
const copilotRecommendations = computed(() => {
  if (!copilot.value) return recommendations.value;
  return [
    {
      type: copilot.value.deal_risk.level === "high" ? "warning" : "info",
      title: "AI Deal Risk",
      description: `${copilot.value.deal_risk.level}: ${copilot.value.deal_risk.reason}`,
    },
    {
      type: "success",
      title: "AI Next Best Action",
      description: copilot.value.next_best_action,
    },
    {
      type: "info",
      title: "Follow-up Draft",
      description: copilot.value.follow_up_draft,
    },
    {
      type: "info",
      title: "Meeting Prep",
      description: copilot.value.meeting_prep,
    },
  ];
});
const pendingCopilotActions = computed(() => (copilot.value?.actions ?? []).filter((action) => action.status === "pending"));

const timelineRows = computed(() => {
  const fallback = [
    { id: "call", when: "Сегодня\n10:30", icon: "phone", title: "Позвонили клиенту", by: "Иван П." },
    { id: "email", when: "Вчера\n15:45", icon: "mail", title: "Отправили КП", by: "Иван П." },
    { id: "meet", when: "3 дня назад\n11:20", icon: "check", title: "Встреча с клиентом", by: "Иван П." },
    { id: "contact", when: "12 дней назад\n09:15", icon: "person", title: "Первый контакт", by: "Иван П." },
    { id: "company", when: "13 дней назад", icon: "building", title: "Создана компания", by: "Система" }
  ];
  if (!activities.value.length) return fallback;
  return activities.value.slice(0, 5).map((activity) => ({
    id: activity.id,
    when: timelineWhen(activity.created_at),
    icon: activity.activity_icon,
    title: activity.title,
    by: activity.author_name ?? "Система"
  }));
});

function formatDate(value?: string | null) {
  if (!value) return "не указано";
  return new Date(value).toLocaleDateString("ru-RU");
}

function relativeDate(value?: string | null) {
  if (!value) return "Нет данных";
  const days = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 86_400_000));
  if (days === 0) return "Сегодня";
  if (days === 1) return "Вчера";
  return `${days} дней назад`;
}

function timelineWhen(value: string) {
  return `${relativeDate(value)}\n${new Date(value).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}`;
}

function formatFileSize(value: number | null) {
  if (!value) return "";
  if (value < 1_000_000) return `${Math.round(value / 1000)} KB`;
  return `${(value / 1_000_000).toFixed(1)} MB`;
}

function close() {
  emit("close");
}

async function reloadWorkspace() {
  if (!props.company) return;
  await crmStore.refreshAll();
  await crmStore.loadCompanyWorkspace(props.company.id);
  await crmStore.refreshCompanyCopilot(props.company.id);
}

async function runDrawerAction(action: () => Promise<void>) {
  if (!props.company) return;
  isSaving.value = true;
  crmStore.error.value = "";
  crmStore.ok.value = "";
  try {
    await action();
    await reloadWorkspace();
    crmStore.ok.value = "Company workspace updated";
  } catch (caught) {
    crmStore.error.value = caught instanceof Error ? caught.message : "Unknown error";
  } finally {
    isSaving.value = false;
  }
}

async function createActivity(type: string, channel: string, title: string, description: string) {
  if (!props.company) return;
  await api<Activity>(
    "/activities",
    post({
      company_id: props.company.id,
      contact_id: contacts.value[0]?.id ?? null,
      deal_id: currentDeal.value?.id ?? null,
      type,
      channel,
      title,
      description,
      metadata: { source: "company_modal" }
    }),
    crmStore.token.value,
    crmStore.tenantId.value
  );
}

function logCall() {
  void runDrawerAction(() => createActivity("CALL", "Call", "Call completed", `Next action: ${nextAction.value}`));
}

function logEmail() {
  void runDrawerAction(() => createActivity("EMAIL", "Email", "Email sent", `Follow-up email for ${workspace.value?.company.name ?? "company"}`));
}

function logMeeting() {
  void runDrawerAction(() => createActivity("MEETING", "Meeting", "Meeting scheduled", "Meeting was planned from company modal."));
}

function addQuickTask() {
  if (!props.company) return;
  void runDrawerAction(async () => {
    await api<Task>(
      "/sales/tasks",
      post(emptyToNull({
        company_id: props.company?.id,
        deal_id: currentDeal.value?.id ?? "",
        title: nextAction.value,
        description: "Created from company modal quick action.",
        priority: "high",
        due_at: ""
      })),
      crmStore.token.value,
      crmStore.tenantId.value
    );
  });
}

function logNote() {
  void runDrawerAction(() => createActivity("COMMENT", "Message", "Note added", "Quick note from company modal."));
}

function openDrawerAction(mode: "call" | "email" | "meeting" | "task") {
  drawerActionMode.value = mode;
  callForm.value.phone = contacts.value[0]?.phone ?? "";
  emailForm.value.recipient = contacts.value[0]?.email ?? "";
  emailForm.value.body = copilot.value?.follow_up_draft ?? `Здравствуйте! Следующий шаг: ${nextAction.value}.`;
  drawerTaskForm.value.title = nextAction.value;
}

async function saveCommunication(
  channel: string,
  subject: string,
  body: string,
  occurredAt?: string,
  recipient?: string
) {
  const event = await api<CommunicationEvent>(
    "/communication/events",
    post(emptyToNull({
      channel,
      direction: "outbound",
      sender: crmStore.me.value?.email ?? "",
      recipient: recipient ?? "",
      subject,
      body,
      occurred_at: occurredAt ?? "",
      company_id: props.company?.id,
      contact_id: contacts.value[0]?.id ?? "",
      deal_id: currentDeal.value?.id ?? "",
      metadata: { source: "company_drawer", draft: channel === "email" }
    })),
    crmStore.token.value,
    crmStore.tenantId.value
  );
  await api<CommunicationEvent>(
    `/communication/events/${event.id}/activity`,
    post({}),
    crmStore.token.value,
    crmStore.tenantId.value
  );
}

function saveCall() {
  void runDrawerAction(async () => {
    await saveCommunication("call", callForm.value.subject, callForm.value.body, undefined, callForm.value.phone);
    drawerActionMode.value = null;
  });
}

function saveEmailDraft() {
  void runDrawerAction(async () => {
    await saveCommunication("email", emailForm.value.subject, emailForm.value.body, undefined, emailForm.value.recipient);
    drawerActionMode.value = null;
  });
}

function saveMeeting() {
  void runDrawerAction(async () => {
    await saveCommunication("meeting", meetingActionForm.value.subject, meetingActionForm.value.body, meetingActionForm.value.occurred_at);
    drawerActionMode.value = null;
  });
}

function saveDrawerTask() {
  void runDrawerAction(async () => {
    await api<Task>(
      "/sales/tasks",
      post(emptyToNull({
        ...drawerTaskForm.value,
        company_id: props.company?.id,
        deal_id: currentDeal.value?.id ?? ""
      })),
      crmStore.token.value,
      crmStore.tenantId.value
    );
    drawerActionMode.value = null;
  });
}

function addProposalFile() {
  if (!props.company) return;
  void runDrawerAction(async () => {
    const file = await api<CompanyFile>(
      `/sales/companies/${props.company?.id}/files`,
      post({
        company_id: props.company?.id,
        deal_id: currentDeal.value?.id ?? null,
        contact_id: contacts.value[0]?.id ?? null,
        activity_id: null,
        name: `Proposal_${props.company?.name}.pdf`,
        file_type: "proposal",
        mime_type: "application/pdf",
        file_size: 1480000,
        storage_key: `demo/${props.company?.id}/proposal.pdf`,
        download_url: `/demo-files/${props.company?.id}/proposal`,
      }),
      crmStore.token.value,
      crmStore.tenantId.value
    );
    await api<KnowledgeDocument>(
      `/knowledge/companies/${props.company?.id}/documents`,
      post({
        title: `Proposal knowledge: ${props.company?.name}`,
        source_type: "proposal",
        visibility: "company",
        company_id: props.company?.id,
        deal_id: currentDeal.value?.id ?? null,
        file_id: file.id,
        text: `Proposal for ${props.company?.name}. Deal: ${currentDeal.value?.title ?? "not set"}. Next action: ${nextAction.value}. Risk: ${currentDeal.value?.risk_level ?? "not set"}. This document belongs to company-specific RAG context.`,
      }),
      crmStore.token.value,
      crmStore.tenantId.value
    );
  });
}

function confirmCopilotAction(actionId: string) {
  void runDrawerAction(() => crmStore.confirmAgentAction(actionId));
}

function rejectCopilotAction(actionId: string) {
  void runDrawerAction(() => crmStore.rejectAgentAction(actionId));
}

function completeNextAction() {
  if (!nextActionRecord.value) return;
  void runDrawerAction(async () => {
    await api<NextAction>(
      `/sales/next-actions/${nextActionRecord.value?.id}/done`,
      post({ is_done: true }, "PATCH"),
      crmStore.token.value,
      crmStore.tenantId.value
    );
  });
}

function openNextActionEditor() {
  nextActionForm.value = {
    title: nextActionRecord.value?.title ?? nextAction.value,
    description: nextActionRecord.value?.description ?? "",
    due_at: nextActionRecord.value?.due_at?.slice(0, 16) ?? "",
    priority: nextActionRecord.value?.priority ?? "high"
  };
  isNextActionEditorOpen.value = true;
}

function saveNextAction() {
  if (!props.company) return;
  void runDrawerAction(async () => {
    const previousActionId = nextActionRecord.value?.id;
    await api<NextAction>(
      "/sales/next-actions",
      post(emptyToNull({
        ...nextActionForm.value,
        company_id: props.company?.id,
        deal_id: currentDeal.value?.id ?? "",
        contact_id: contacts.value[0]?.id ?? "",
        source: "manual"
      })),
      crmStore.token.value,
      crmStore.tenantId.value
    );
    if (previousActionId) {
      await api<NextAction>(
        `/sales/next-actions/${previousActionId}/done`,
        post({ is_done: true }, "PATCH"),
        crmStore.token.value,
        crmStore.tenantId.value
      );
    }
    isNextActionEditorOpen.value = false;
  });
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
            <span class="ref-chip">{{ companyType }}</span>
            <span class="ref-chip success">{{ workspace.company.status_label ?? workspace.company.status }}</span>
          </div>
          <p class="ref-subline">{{ displayIndustry }} <span></span> Клиент с {{ formatDate(clientSince) }}</p>
          <div class="ref-actions">
            <button type="button" class="ref-primary-action" :disabled="isSaving" @click="openDrawerAction('call')"><span class="ui-icon phone"></span>Позвонить</button>
            <button type="button" class="ref-action" :disabled="isSaving" @click="openDrawerAction('email')"><span class="ui-icon mail"></span>Generate Email</button>
            <button type="button" class="ref-action" :disabled="isSaving" @click="openDrawerAction('meeting')"><span class="ui-icon calendar"></span>Встреча</button>
            <button type="button" class="ref-action" :disabled="isSaving" @click="openDrawerAction('task')"><span class="ui-icon task"></span>Задача</button>
            <RouterLink class="ref-action" :to="{ path: `/companies/${company.id}`, query: { tab: 'knowledge' } }"><span class="ui-icon file"></span>Knowledge</RouterLink>
            <button type="button" class="ref-action icon-only" :disabled="isSaving" @click="logNote">...</button>
          </div>
        </div>

        <dl class="reference-kpis">
          <div><dt>Health</dt><dd>{{ health }} <span>{{ healthTrend }}</span></dd><small>{{ healthLabel }}</small></div>
          <div><dt>Revenue</dt><dd>{{ crmStore.money(pipeline || 50000) }}</dd></div>
          <div><dt>Open Tasks</dt><dd>{{ openTasks.length || 2 }}</dd></div>
          <div><dt>Owner</dt><dd class="owner-kpi"><span class="avatar-mini">{{ ownerInitials }}</span> {{ ownerName }}</dd></div>
        </dl>

        <div class="reference-window-actions">
          <button type="button" class="plain-icon">⋮</button>
          <button type="button" class="plain-icon close-x" @click="close">×</button>
        </div>
      </header>

      <section v-if="drawerActionMode" class="drawer-action-panel">
        <header><h2>{{ drawerActionMode === "call" ? "Call" : drawerActionMode === "email" ? "Email draft" : drawerActionMode === "meeting" ? "Meeting" : "Task" }}</h2><button class="secondary" type="button" @click="drawerActionMode = null">Close</button></header>
        <form v-if="drawerActionMode === 'call'" class="compact-form" @submit.prevent="saveCall">
          <label>Телефон<input v-model="callForm.phone" type="tel" /></label><label>Тема<input v-model="callForm.subject" /></label><label>Результат<textarea v-model="callForm.body"></textarea></label>
          <div class="button-row"><a v-if="callForm.phone" class="button-link" :href="`tel:${callForm.phone}`">Начать звонок</a><button type="submit">Сохранить результат</button></div>
        </form>
        <form v-else-if="drawerActionMode === 'email'" class="compact-form" @submit.prevent="saveEmailDraft">
          <label>Получатель<input v-model="emailForm.recipient" type="email" /></label><label>Тема<input v-model="emailForm.subject" /></label><label>AI draft<textarea v-model="emailForm.body" rows="7"></textarea></label><button type="submit">Сохранить draft</button>
        </form>
        <form v-else-if="drawerActionMode === 'meeting'" class="compact-form" @submit.prevent="saveMeeting">
          <label>Название<input v-model="meetingActionForm.subject" /></label><label>Дата<input v-model="meetingActionForm.occurred_at" type="datetime-local" required /></label><label>Повестка<textarea v-model="meetingActionForm.body"></textarea></label><button type="submit">Запланировать</button>
        </form>
        <form v-else class="compact-form" @submit.prevent="saveDrawerTask">
          <label>Задача<input v-model="drawerTaskForm.title" /></label><label>Описание<textarea v-model="drawerTaskForm.description"></textarea></label><label>Срок<input v-model="drawerTaskForm.due_at" type="datetime-local" /></label><label>Приоритет<select v-model="drawerTaskForm.priority"><option value="normal">Normal</option><option value="high">High</option><option value="urgent">Urgent</option></select></label><button type="submit">Создать задачу</button>
        </form>
      </section>

      <main class="reference-body">
        <section class="reference-main">
          <div class="reference-top-grid">
            <section class="ref-card next-focus">
              <p class="ref-card-label"><span class="flame-dot"></span>Следующее действие</p>
              <h2>{{ nextAction }}</h2>
              <p>{{ lastContactAt }} после последнего контакта.</p>
              <form v-if="isNextActionEditorOpen" class="next-action-editor" @submit.prevent="saveNextAction">
                <label>Действие<input v-model="nextActionForm.title" required minlength="2" /></label>
                <label>Описание<textarea v-model="nextActionForm.description" rows="2"></textarea></label>
                <div>
                  <label>Срок<input v-model="nextActionForm.due_at" type="datetime-local" /></label>
                  <label>Приоритет
                    <select v-model="nextActionForm.priority">
                      <option value="low">Low</option>
                      <option value="normal">Normal</option>
                      <option value="high">High</option>
                    </select>
                  </label>
                </div>
                <div class="button-row">
                  <button type="submit" :disabled="isSaving">Сохранить</button>
                  <button class="secondary" type="button" @click="isNextActionEditorOpen = false">Отмена</button>
                </div>
              </form>
              <div v-else class="button-row next-action-buttons">
                <button v-if="nextActionRecord" type="button" class="call-split" :disabled="isSaving" @click="completeNextAction"><span class="ui-icon check"></span>Выполнено</button>
                <button type="button" class="ref-action" :disabled="isSaving" @click="openNextActionEditor">{{ nextActionRecord ? "Заменить" : "Создать действие" }}</button>
              </div>
            </section>

            <section class="ref-card deal-focus-card">
              <div class="ref-card-head">
                <div>
                  <p class="ref-card-label">Текущая сделка</p>
                  <h2>{{ currentDeal?.title ?? "Активная сделка" }}</h2>
                </div>
                <RouterLink
                  class="ref-action"
                  :to="currentDeal ? { path: '/deals', query: { deal: currentDeal.id, from: 'company' } } : '/deals'"
                >
                  Открыть сделку
                </RouterLink>
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
                <div><span>Вероятность</span><strong>{{ dealProbability ?? 50 }}%</strong></div>
                <div><span>Сумма</span><strong>{{ crmStore.money(currentDeal?.amount ?? 50000) }}</strong></div>
              </div>
              <footer class="deal-footer">
                <span><span class="ui-icon calendar"></span>Следующий шаг: <strong>{{ nextAction }}</strong></span>
                <span>{{ expectedNextEvent }}</span>
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
            <div><span>Последний контакт</span><strong class="danger-text">{{ lastContactAt }}</strong><small>{{ lastContactPerson }}</small></div>
            <div><span>Возраст сделки</span><strong>{{ currentDealAge }}</strong><small>с {{ formatDate(currentDeal?.created_at ?? clientSince) }}</small></div>
            <div><span>Канал</span><strong>{{ channelSummary }}</strong><small>{{ activities.length }} активности</small></div>
            <div><span>Источник</span><strong>{{ source }}</strong><small>Лид / компания</small></div>
            <div><span>Индустрия</span><strong>{{ displayIndustry }}</strong><small>{{ companyType }}</small></div>
          </section>
        </section>

        <aside class="reference-side">
          <section class="ref-card compact-side">
            <p class="ref-card-label sparkle">AI рекомендации</p>
            <article v-if="copilot" class="side-recommendation info"><span class="round-icon">i</span><div><strong>AI Summary</strong><small>{{ copilot.summary }}</small></div><span>›</span></article>
            <article v-for="item in copilotRecommendations" :key="item.title" class="side-recommendation" :class="item.type ?? 'info'"><span class="round-icon">i</span><div><strong>{{ item.title }}</strong><small>{{ item.description }}</small></div><span>›</span></article>
            <article v-if="!copilotRecommendations.length" class="side-recommendation info"><span class="round-icon">i</span><div><strong>Нет рекомендаций</strong><small>Данных пока недостаточно</small></div><span>›</span></article>
            <article v-for="action in pendingCopilotActions" :key="action.id" class="side-recommendation info">
              <span class="round-icon">AI</span>
              <div>
                <strong>{{ String(action.action_type).replace(/_/g, " ") }}</strong>
                <small>{{ String(action.payload.title ?? action.payload.risk_level ?? "AI action") }}</small>
                <div class="button-row">
                  <button type="button" class="secondary" :disabled="isSaving" @click="confirmCopilotAction(action.id)">Confirm</button>
                  <button type="button" class="secondary" :disabled="isSaving" @click="rejectCopilotAction(action.id)">Reject</button>
                </div>
              </div>
              <span>›</span>
            </article>
            <article v-if="workspace.health.success_chance != null" class="side-recommendation success"><span class="round-icon">↗</span><div><strong>Шанс на успех</strong><small>{{ workspace.health.success_chance }}%</small></div><strong class="green-text">↑ {{ workspace.health.success_chance_delta ?? 0 }}%</strong></article>
          </section>

          <section class="ref-card compact-side">
            <div class="side-head"><p class="ref-card-label">Контакты ({{ contacts.length || 2 }})</p><button type="button">+ Добавить</button></div>
            <article v-for="contact in contacts.slice(0, 2)" :key="contact.id" class="contact-line">
              <span class="contact-avatar">{{ contact.name.slice(0, 2).toUpperCase() }}</span>
              <div><strong>{{ contact.name }}</strong><small>{{ contact.role ?? contact.company_name ?? "Менеджер" }}</small></div>
              <span v-if="contact.actions?.call" class="mini-action">⌕</span><span v-if="contact.actions?.email" class="mini-action">✉</span><span v-if="contact.actions?.more" class="mini-action">...</span>
            </article>
            <article v-if="!contacts.length" class="contact-line">
              <span class="contact-avatar">ИИ</span><div><strong>Иван Иванов</strong><small>CEO</small></div><span class="mini-action">⌕</span><span class="mini-action">✉</span><span class="mini-action">...</span>
            </article>
            <article v-if="contacts.length < 2" class="contact-line">
              <span class="contact-avatar blue">АП</span><div><strong>Алексей Петров</strong><small>Менеджер</small></div><span class="mini-action">⌕</span><span class="mini-action">✉</span><span class="mini-action">...</span>
            </article>
          </section>

          <section class="ref-card compact-side">
            <div class="side-head"><p class="ref-card-label">Задачи ({{ openTasks.length || 1 }})</p><button type="button" :disabled="isSaving" @click="addQuickTask">+ Добавить</button></div>
            <article class="task-line">
              <span class="task-circle"></span>
              <div><strong>{{ nextAction }}</strong><small>Сегодня</small></div>
              <span class="priority">High</span>
            </article>
          </section>

          <section class="ref-card compact-side">
            <div class="side-head"><p class="ref-card-label">Файлы ({{ files.length }})</p><button type="button" :disabled="isSaving" @click="addProposalFile">+ Добавить</button></div>
            <article v-for="file in files.slice(0, 3)" :key="file.id" class="file-line"><span class="file-badge pdf">{{ file.file_type ?? "FILE" }}</span><div><strong>{{ file.name }}</strong><small>{{ file.file_type ?? "FILE" }} · {{ formatFileSize(file.file_size) }}</small></div><small>{{ relativeDate(file.uploaded_at) }}</small><span>⇩</span></article>
            <article v-for="document in knowledgeDocuments.slice(0, 2)" :key="document.id" class="file-line"><span class="file-badge pdf">RAG</span><div><strong>{{ document.title }}</strong><small>{{ document.visibility }} · {{ document.chunks_count }} chunks</small></div><small>{{ relativeDate(document.created_at) }}</small><span>⌕</span></article>
            <article v-if="!files.length" class="file-line"><span class="file-badge pdf">--</span><div><strong>Файлов нет</strong><small>Загрузки пока не добавлены</small></div><small></small><span></span></article>
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
