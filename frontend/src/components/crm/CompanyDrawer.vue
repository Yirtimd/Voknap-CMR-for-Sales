<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { api, emptyToNull, post } from "../../api";
import type { Activity, CommunicationEvent, Company, CompanyFile, KnowledgeDocument, NextAction, Task } from "../../types";
import { crmStore } from "../../stores/crm";

const props = defineProps<{ company: Company | null; initialTab?: string }>();
const emit = defineEmits<{ close: [] }>();
const isSaving = ref(false);
const isNextActionEditorOpen = ref(false);
const nextActionForm = ref({ title: "", description: "", due_at: "", priority: "high" });
const drawerActionMode = ref<"call" | "email" | "meeting" | "task" | null>(null);
const callForm = ref({ subject: "Звонок клиенту", body: "", phone: "" });
const emailForm = ref({ subject: "Follow-up", body: "", recipient: "" });
const meetingActionForm = ref({ subject: "Встреча с клиентом", body: "", occurred_at: "" });
const drawerTaskForm = ref({ title: "Follow-up", description: "", due_at: "", priority: "high" });
const activeTab = ref("overview");
const tabs = [
  { code: "overview", label: "Overview" },
  { code: "timeline", label: "Timeline" },
  { code: "contacts", label: "Contacts" },
  { code: "deals", label: "Deals" },
  { code: "tasks", label: "Tasks" },
  { code: "files", label: "Files" },
  { code: "knowledge", label: "Knowledge" },
  { code: "history", label: "History" }
];

watch(
  () => [props.company?.id, props.initialTab],
  ([companyId, tab]) => {
    if (!companyId) return;
    activeTab.value = typeof tab === "string" && tabs.some((item) => item.code === tab) ? tab : "overview";
  },
  { immediate: true }
);

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
const fallbackStages = computed(() => currentStage.value ? [currentStage.value] : []);
const dealStageRows = computed(() =>
  deals.value.length
    ? deals.value.map((deal) => ({
        deal,
        stages: stages.value.length ? stages.value : fallbackStages.value,
        activeIndex: Math.max(0, (stages.value.length ? stages.value : fallbackStages.value).findIndex((stage) => stage.id === deal.stage_id))
      }))
    : []
);
const compactDealRows = computed(() =>
  dealStageRows.value.slice(0, 4).map((row) => {
    const stageCount = Math.max(1, row.stages.length);
    const activeStage = row.stages[row.activeIndex];
    const nextStage = row.stages[row.activeIndex + 1];
    return {
      ...row,
      activeStageName: activeStage?.name ?? "Stage",
      nextStageName: nextStage?.name ?? "Final",
      progress: Math.round(((row.activeIndex + 1) / stageCount) * 100)
    };
  })
);
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
const historyRows = computed(() =>
  activities.value
    .filter((activity) => Array.isArray(activity.metadata?.changes))
    .flatMap((activity) =>
      (activity.metadata.changes as Array<{ field: string; old: unknown; new: unknown }>).map((change) => ({ activity, change }))
    )
);

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

function toggleDrawerTask(task: Task) {
  void runDrawerAction(async () => {
    await api<Task>(
      `/sales/tasks/${task.id}/done`,
      post({ is_done: !task.done_at }, "PATCH"),
      crmStore.token.value,
      crmStore.tenantId.value
    );
  });
}

function askCompanyKnowledge() {
  if (!props.company) return;
  void crmStore.askKnowledge({
    company_id: props.company.id,
    deal_id: currentDeal.value?.id ?? ""
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
      <header class="deal-modal-head">
        <div>
          <p class="deal-modal-label">Company</p>
          <div class="deal-title-row">
            <h1>{{ workspace.company.name }}</h1>
            <button type="button" class="deal-inline-icon">☆</button>
            <button type="button" class="deal-inline-icon" :disabled="isSaving" @click="logNote">...</button>
          </div>
          <p class="deal-subtitle"><span class="ui-icon building"></span>{{ currentDeal?.title ?? "Активная сделка" }} <span>•</span> {{ crmStore.money(pipeline || currentDeal?.amount || 0) }}</p>
        </div>

        <div class="deal-window-actions">
          <button type="button" class="ref-action icon-only" :disabled="isSaving" @click="logNote">...</button>
          <button type="button" class="ref-action" @click="openDrawerAction('task')">Edit</button>
          <button type="button" class="ref-action" @click="close">Close <span>×</span></button>
        </div>
      </header>

      <section class="deal-modal-top">
        <section class="deal-probability-card">
          <p class="deal-card-label">AI Probability</p>
          <div class="deal-probability-line">
            <strong>{{ dealProbability ?? health }}%</strong>
            <span>↑ {{ workspace.health.success_chance_delta ?? 12 }}%</span>
          </div>
          <div class="deal-probability-bar"><span :style="{ width: `${dealProbability ?? health}%` }"></span></div>
          <small><span class="chance-dot"></span>{{ healthLabel }} chance</small>
        </section>

        <section class="deal-mini-card">
          <p>Amount</p>
          <strong>{{ crmStore.money(currentDeal?.amount ?? pipeline) }}</strong>
          <small>Expected close</small>
          <b><span class="ui-icon calendar"></span>{{ formatDate(currentDeal?.expected_close_date ?? currentDeal?.created_at ?? clientSince) }}</b>
        </section>

        <section class="deal-mini-card">
          <p>Stage</p>
          <strong>{{ currentStage?.name ?? "Proposal" }}</strong>
          <span class="deal-status-pill">{{ currentDeal?.status ?? "Open" }}</span>
        </section>

        <section class="deal-mini-card">
          <p>Owner</p>
          <div class="deal-owner-row"><span class="avatar-mini">{{ ownerInitials }}</span><strong>{{ ownerName }}</strong></div>
          <small>Sales</small>
        </section>

        <section class="deal-mini-card">
          <p>Last activity</p>
          <strong>{{ lastContactAt }}</strong>
          <small><span class="green-dot"></span>{{ channelSummary }}</small>
        </section>

        <aside class="deal-next-card">
          <p class="deal-card-label">Next action</p>
          <div>
            <span class="next-calendar">□</span>
            <div>
              <strong>{{ nextAction }}</strong>
              <small>{{ formatDate(nextActionRecord?.due_at ?? clientSince) }}</small>
            </div>
          </div>
          <footer>
            <button type="button" :disabled="isSaving" @click="completeNextAction">✓ Mark as done</button>
            <button type="button" class="secondary" @click="openNextActionEditor"><span class="ui-icon calendar"></span>Reschedule</button>
          </footer>
        </aside>

        <section class="deal-stage-card compact-deals-progress">
          <header>
            <div>
              <p class="deal-card-label">Deals progress</p>
              <strong>{{ deals.length }} {{ deals.length === 1 ? "deal" : "deals" }}</strong>
            </div>
            <button type="button" @click="activeTab = 'deals'">View all</button>
          </header>
          <article v-for="row in compactDealRows.slice(0, 1)" :key="row.deal.id" class="compact-deal-progress-row">
            <header>
              <div>
                <strong>{{ row.deal.title }}</strong>
                <small>{{ row.activeStageName }} → {{ row.nextStageName }}</small>
              </div>
              <small>{{ crmStore.money(row.deal.amount) }}</small>
            </header>
            <div class="compact-deal-progress-meta">
              <span class="deal-status-pill">{{ row.activeStageName }}</span>
              <span>{{ row.progress }}%</span>
            </div>
            <div class="compact-deal-progress-line"><span :style="{ width: `${row.progress}%` }"></span></div>
          </article>
          <button v-if="deals.length > 1" type="button" class="more-deals-row" @click="activeTab = 'deals'">
            + {{ deals.length - 1 }} more {{ deals.length - 1 === 1 ? "deal" : "deals" }}
            <span>Open deals</span>
          </button>
          <p v-if="!dealStageRows.length" class="empty">У компании пока нет сделок</p>
        </section>

        <aside class="deal-open-tasks-card">
          <header><p class="deal-card-label">Open Tasks ({{ openTasks.length || 1 }})</p><button type="button" @click="activeTab = 'tasks'">View all</button></header>
          <article>
            <span class="task-circle"></span>
            <div><strong>{{ openTasks[0]?.title ?? "Подготовить демонстрацию" }}</strong><small>{{ openTasks[0]?.due_at ? formatDate(openTasks[0].due_at) : "Jul 10" }} • {{ ownerName }}</small></div>
            <span class="priority">Medium</span>
          </article>
        </aside>
      </section>

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

      <nav class="reference-tabs" aria-label="Company workspace sections">
        <button v-for="tab in tabs" :key="tab.code" type="button" :class="{ active: activeTab === tab.code }" @click="activeTab = tab.code">{{ tab.label }}</button>
      </nav>

      <main v-if="activeTab === 'overview'" class="deal-overview-grid">
        <section class="deal-section-card deal-details-card">
          <h2>Deal Details</h2>
          <dl>
            <div><dt>Type</dt><dd>New Business</dd></div>
            <div><dt>Source</dt><dd>{{ source }}</dd></div>
            <div><dt>Pipeline</dt><dd>Sales Pipeline</dd></div>
            <div><dt>Tags</dt><dd><span class="detail-tag">CRM</span><span class="detail-tag">{{ companyType }}</span><span class="detail-tag">+1</span></dd></div>
            <div><dt>Products</dt><dd>CRM Platform</dd></div>
            <div><dt>Discount</dt><dd>10%</dd></div>
            <div><dt>Forecast category</dt><dd>Commit</dd></div>
            <div><dt>Probability (manual)</dt><dd>{{ dealProbability ?? 60 }}%</dd></div>
          </dl>
        </section>

        <section class="deal-section-card ai-insight-card">
          <h2>AI Insights</h2>
          <article>
            <p class="insight-title">✦ Рекомендация</p>
            <p>{{ copilot?.next_best_action ?? "Проведите встречу с директором на этой неделе. Это повысит вероятность закрытия на 18%." }}</p>
            <hr />
            <p class="insight-subtitle">Что влияет на сделку</p>
            <ul>
              <li>Клиент активно отвечает на письма</li>
              <li>Бюджет подтвержден, решение централизованное</li>
            </ul>
            <button type="button">See details⌄</button>
          </article>
        </section>

        <section class="deal-section-card stakeholders-card">
          <header><h2>People & Stakeholders</h2><button type="button">View all</button></header>
          <article v-for="contact in contacts.slice(0, 3)" :key="contact.id">
            <span class="stakeholder-avatar">{{ contact.name.slice(0, 2).toUpperCase() }}</span>
            <div><strong>{{ contact.name }}</strong><small>{{ contact.role ?? contact.company_name ?? "Контакт" }}</small></div>
            <em>{{ contact.role ?? "User" }}</em>
          </article>
          <article v-if="!contacts.length"><span class="stakeholder-avatar">АК</span><div><strong>Алексей Кузнецов</strong><small>Директор по IT</small></div><em>Decision Maker</em></article>
          <article v-if="contacts.length < 2"><span class="stakeholder-avatar">ЕЕ</span><div><strong>Елена Иванова</strong><small>Руководитель отдела продаж</small></div><em class="warn">Influencer</em></article>
          <article v-if="contacts.length < 3"><span class="stakeholder-avatar">SS</span><div><strong>Сергей Смирнов</strong><small>IT-специалист</small></div><em class="muted">User</em></article>
        </section>

        <section class="deal-section-card notes-card">
          <header><h2>Notes & Activity</h2><button type="button" @click="activeTab = 'timeline'">View all</button></header>
          <input placeholder="Add note..." />
          <article v-for="row in timelineRows.slice(0, 3)" :key="row.id">
            <span class="activity-dot"></span>
            <div><strong>{{ row.title }}</strong><small>{{ row.by }} • {{ String(row.when).split('\n')[0] }}</small></div>
          </article>
        </section>

        <section class="deal-section-card risks-card">
          <header><h2>Risks & Blockers</h2><button type="button">View all</button></header>
          <article><span class="risk-icon high">△</span><div><strong>Нет встречи с директором</strong><small>Ключевое лицо не вовлечено в процесс</small></div><em>High</em></article>
          <article><span class="risk-icon medium">△</span><div><strong>Конкурент предложил демо</strong><small>Возможна потеря интереса клиента</small></div><em class="medium">Medium</em></article>
          <article><span class="risk-icon low">i</span><div><strong>Ожидаем внутреннее согласование</strong><small>Может повлиять на дату закрытия</small></div><em class="low">Low</em></article>
        </section>

        <section class="deal-section-card documents-card">
          <header><h2>Files & Documents</h2><button type="button" @click="activeTab = 'files'">View all</button></header>
          <article v-for="file in files.slice(0, 3)" :key="file.id"><span class="doc-icon">▧</span><div><strong>{{ file.name }}</strong><small>{{ relativeDate(file.uploaded_at) }} • {{ formatFileSize(file.file_size) }}</small></div><span>⇩</span></article>
          <article v-for="document in knowledgeDocuments.slice(0, 2)" :key="document.id"><span class="doc-icon">▧</span><div><strong>{{ document.title }}</strong><small>{{ document.visibility }} • {{ document.chunks_count }} chunks</small></div><span>⇩</span></article>
          <article v-if="!files.length && !knowledgeDocuments.length"><span class="doc-icon">▧</span><div><strong>Коммерческое предложение.pdf</strong><small>Jul 07 • {{ ownerName }}</small></div><span>⇩</span></article>
          <article v-if="!files.length && !knowledgeDocuments.length"><span class="doc-icon">▧</span><div><strong>Презентация CRM.pdf</strong><small>Jul 05 • {{ ownerName }}</small></div><span>⇩</span></article>
        </section>
      </main>

      <main v-else class="reference-tab-body">
        <section v-if="activeTab === 'timeline'" class="ref-card tab-panel">
          <h2>Timeline</h2>
          <article v-for="row in timelineRows" :key="row.id" class="history-row"><time>{{ row.when }}</time><span class="history-node"></span><span class="ui-icon" :class="row.icon"></span><div><strong>{{ row.title }}</strong><small>{{ row.by }}</small></div></article>
        </section>

        <section v-else-if="activeTab === 'contacts'" class="ref-card tab-panel">
          <h2>Contacts</h2>
          <article v-for="contact in contacts" :key="contact.id" class="entity-row"><div><strong>{{ contact.name }}</strong><small>{{ contact.role ?? "Contact" }} · {{ contact.email ?? "no email" }} · {{ contact.phone ?? "no phone" }}</small></div></article>
          <p v-if="!contacts.length" class="empty">No contacts</p>
        </section>

        <section v-else-if="activeTab === 'deals'" class="ref-card tab-panel">
          <h2>Deals</h2>
          <RouterLink v-for="deal in deals" :key="deal.id" class="entity-row drawer-row-link" :to="{ path: '/deals', query: { deal: deal.id } }"><div><strong>{{ deal.title }}</strong><small>{{ stages.find((stage) => stage.id === deal.stage_id)?.name ?? "Stage" }} · {{ deal.status }}</small></div><b>{{ crmStore.money(deal.amount) }}</b></RouterLink>
          <p v-if="!deals.length" class="empty">No deals</p>
        </section>

        <section v-else-if="activeTab === 'tasks'" class="ref-card tab-panel">
          <h2>Tasks</h2>
          <article v-for="task in tasks" :key="task.id" class="entity-row"><div><strong>{{ task.title }}</strong><small>{{ task.priority }} · {{ task.due_at ? new Date(task.due_at).toLocaleString('ru-RU') : "no due date" }}</small></div><button class="secondary" type="button" @click="toggleDrawerTask(task)">{{ task.done_at ? "Reopen" : "Done" }}</button></article>
          <p v-if="!tasks.length" class="empty">No tasks</p>
        </section>

        <section v-else-if="activeTab === 'files'" class="ref-card tab-panel">
          <h2>Files</h2>
          <article v-for="file in files" :key="file.id" class="entity-row"><div><strong>{{ file.name }}</strong><small>{{ file.file_type ?? "file" }} · {{ formatFileSize(file.file_size) }}</small></div><a v-if="file.download_url" class="button-link secondary-link" :href="file.download_url">Open</a></article>
          <p v-if="!files.length" class="empty">No files</p>
        </section>

        <section v-else-if="activeTab === 'knowledge'" class="reference-knowledge-grid">
          <section class="ref-card tab-panel"><h2>Company Knowledge</h2><p class="hint">Scope: {{ workspace.company.name }}{{ currentDeal ? ` · ${currentDeal.title}` : "" }}</p><article v-for="document in knowledgeDocuments" :key="document.id" class="entity-row"><div><strong>{{ document.title }}</strong><small>{{ document.visibility }} · {{ document.chunks_count }} chunks</small></div></article><p v-if="!knowledgeDocuments.length" class="empty">No company documents</p></section>
          <section class="ref-card tab-panel"><h2>Ask Knowledge</h2><label>Question<textarea v-model="crmStore.knowledgeAskForm.value.question" rows="4"></textarea></label><button type="button" @click="askCompanyKnowledge">Ask company knowledge</button><p v-if="crmStore.knowledgeAnswer.value" class="answer-text">{{ crmStore.knowledgeAnswer.value.answer }}</p><article v-for="citation in crmStore.knowledgeAnswer.value?.citations ?? []" :key="citation.chunk_id" class="citation-row"><strong>{{ citation.document_title }}</strong><small>{{ citation.document_scope }}</small><p>{{ citation.text }}</p></article></section>
        </section>

        <section v-else class="ref-card tab-panel">
          <h2>Change History</h2>
          <article v-for="row in historyRows" :key="`${row.activity.id}-${row.change.field}`" class="history-change-row"><span>{{ row.change.field.replace(/_/g, " ") }}</span><div><strong>{{ row.change.old ?? "empty" }}</strong><small>changed to</small><strong>{{ row.change.new ?? "empty" }}</strong></div><small>{{ new Date(row.activity.created_at).toLocaleString("ru-RU") }}</small></article>
          <p v-if="!historyRows.length" class="empty">No tracked changes</p>
        </section>
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
