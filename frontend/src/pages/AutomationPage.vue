<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import { automationStore } from "../stores/automation";
import { crmStore } from "../stores/crm";
import type {
  AutomationActionType,
  AutomationConditionOperator,
  AutomationMessageTemplate,
  AutomationTriggerType,
  AutomationWorkflow
} from "../types";

type Tab = "workflows" | "templates" | "runs" | "approvals" | "outbox";
type ConditionDraft = { field: string; operator: AutomationConditionOperator; value: string };
type ActionDraft = { type: AutomationActionType; config: string };

const tabs: Array<{ id: Tab; label: string }> = [
  { id: "workflows", label: "Сценарии" },
  { id: "templates", label: "Шаблоны" },
  { id: "runs", label: "Запуски" },
  { id: "approvals", label: "Согласования" },
  { id: "outbox", label: "Outbox" }
];
const triggers: Array<{ value: AutomationTriggerType; label: string }> = [
  { value: "lead.created", label: "Создан лид" },
  { value: "deal.created", label: "Создана сделка" },
  { value: "deal.updated", label: "Изменена сделка" },
  { value: "deal.stage_changed", label: "Изменён этап сделки" },
  { value: "communication.created", label: "Создана коммуникация" },
  { value: "schedule.deal_inactive", label: "Сделка без активности" }
];
const operators: AutomationConditionOperator[] = ["eq", "neq", "gt", "gte", "lt", "lte", "in", "contains", "is_empty"];
const actionTypes: Array<{ value: AutomationActionType; label: string; example: string }> = [
  { value: "assign_owner", label: "Назначить владельца", example: '{"assignee":"owner_manager"}' },
  { value: "create_task", label: "Создать задачу", example: '{"title":"Связаться по {{title}}","assignee":"owner","due_in_days":1}' },
  { value: "send_template", label: "Отправить шаблон", example: '{"template_id":"UUID"}' },
  { value: "request_approval", label: "Запросить согласование", example: '{"title":"Согласовать скидку","assignee":"owner_manager"}' },
  { value: "update_next_action", label: "Обновить next action", example: '{"title":"Позвонить клиенту","assignee":"owner","due_in_days":1}' }
];

const activeTab = ref<Tab>("workflows");
const profileError = ref("");
const localError = ref("");
const scheduledSummary = ref("");
const runFilter = ref("");
const approvalFilter = ref("");
const outboxFilter = ref("");
const approvalComments = reactive<Record<string, string>>({});
const outboxErrors = reactive<Record<string, string>>({});
const editingWorkflowId = ref("");
const editingTemplateId = ref("");

const workflowForm = reactive({
  name: "",
  description: "",
  trigger_type: "lead.created" as AutomationTriggerType,
  condition_logic: "all" as "all" | "any",
  priority: 100,
  is_active: true,
  conditions: [] as ConditionDraft[],
  actions: [newAction("create_task")] as ActionDraft[]
});
const templateForm = reactive({ name: "", channel: "email", subject: "", body: "", is_active: true });

const editingWorkflow = computed(() =>
  automationStore.workflows.value.find((item) => item.id === editingWorkflowId.value)
);
const denied = computed(() => !automationStore.canOpen.value && !profileError.value);

onMounted(async () => {
  try {
    await crmStore.refreshMe();
  } catch {
    profileError.value = "Не удалось загрузить /me. Войдите заново или проверьте актуальность API.";
  }
  await automationStore.refreshAll();
  if (!automationStore.canManageAutomations.value && automationStore.canManageApprovals.value) activeTab.value = "approvals";
});

function newAction(type: AutomationActionType): ActionDraft {
  return { type, config: actionTypes.find((item) => item.value === type)?.example ?? "{}" };
}

function addCondition() {
  workflowForm.conditions.push({ field: "", operator: "eq", value: "" });
}

function addAction() {
  workflowForm.actions.push(newAction("create_task"));
}

function changeActionType(action: ActionDraft) {
  action.config = actionTypes.find((item) => item.value === action.type)?.example ?? "{}";
}

function parseConditionValue(condition: ConditionDraft) {
  if (condition.operator === "is_empty") return undefined;
  const value = condition.value.trim();
  if (!value) return "";
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return value;
  }
}

function workflowPayload() {
  return {
    name: workflowForm.name,
    description: workflowForm.description || null,
    trigger_type: workflowForm.trigger_type,
    condition_logic: workflowForm.condition_logic,
    priority: workflowForm.priority,
    is_active: workflowForm.is_active,
    conditions: workflowForm.conditions.map((item) => ({
      field: item.field,
      operator: item.operator,
      value: parseConditionValue(item)
    })),
    actions: workflowForm.actions.map((item) => {
      const config = JSON.parse(item.config) as unknown;
      if (!config || typeof config !== "object" || Array.isArray(config)) throw new Error("Настройки действия должны быть JSON-объектом.");
      return { type: item.type, config: config as Record<string, unknown> };
    })
  };
}

async function saveWorkflow() {
  await guarded(async () => {
    const payload = workflowPayload();
    if (editingWorkflow.value) {
      await automationStore.updateWorkflow(editingWorkflow.value.id, editingWorkflow.value.version, payload);
    } else {
      await automationStore.createWorkflow(payload);
    }
    resetWorkflow();
  });
}

function editWorkflow(workflow: AutomationWorkflow) {
  editingWorkflowId.value = workflow.id;
  workflowForm.name = workflow.name;
  workflowForm.description = workflow.description ?? "";
  workflowForm.trigger_type = workflow.trigger_type;
  workflowForm.condition_logic = workflow.condition_logic;
  workflowForm.priority = workflow.priority;
  workflowForm.is_active = workflow.is_active;
  workflowForm.conditions = workflow.conditions.map((item) => ({
    field: item.field,
    operator: item.operator,
    value: item.value === undefined ? "" : typeof item.value === "string" ? item.value : JSON.stringify(item.value)
  }));
  workflowForm.actions = workflow.actions.map((item) => ({ type: item.type, config: JSON.stringify(item.config, null, 2) }));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function resetWorkflow() {
  editingWorkflowId.value = "";
  workflowForm.name = "";
  workflowForm.description = "";
  workflowForm.trigger_type = "lead.created";
  workflowForm.condition_logic = "all";
  workflowForm.priority = 100;
  workflowForm.is_active = true;
  workflowForm.conditions = [];
  workflowForm.actions = [newAction("create_task")];
}

async function toggleWorkflow(workflow: AutomationWorkflow) {
  await guarded(() => automationStore.updateWorkflow(workflow.id, workflow.version, { is_active: !workflow.is_active }).then(() => undefined));
}

async function saveTemplate() {
  await guarded(async () => {
    const payload = { name: templateForm.name, channel: templateForm.channel, subject: templateForm.subject, body: templateForm.body };
    if (editingTemplateId.value) await automationStore.updateTemplate(editingTemplateId.value, payload);
    else await automationStore.createTemplate(payload);
    resetTemplate();
  });
}

function editTemplate(item: AutomationMessageTemplate) {
  editingTemplateId.value = item.id;
  templateForm.name = item.name;
  templateForm.channel = item.channel;
  templateForm.subject = item.subject;
  templateForm.body = item.body;
  templateForm.is_active = item.is_active;
}

function resetTemplate() {
  editingTemplateId.value = "";
  templateForm.name = "";
  templateForm.channel = "email";
  templateForm.subject = "";
  templateForm.body = "";
  templateForm.is_active = true;
}

async function toggleTemplate(item: AutomationMessageTemplate) {
  await guarded(() => automationStore.updateTemplate(item.id, { is_active: !item.is_active }).then(() => undefined));
}

async function runScheduled() {
  await guarded(async () => {
    const result = await automationStore.runScheduled();
    scheduledSummary.value = `Проверено: ${result.evaluated}, создано запусков: ${result.matched_runs}`;
    activeTab.value = "runs";
  });
}

async function decide(id: string, decision: "approved" | "rejected") {
  await guarded(() => automationStore.decideApproval(id, decision, approvalComments[id]).then(() => undefined));
}

async function markOutbox(id: string, status: "sent" | "failed" | "cancelled") {
  if (status === "failed" && !outboxErrors[id]?.trim()) {
    localError.value = "Для статуса failed укажите ошибку.";
    return;
  }
  await guarded(() => automationStore.updateOutbox(id, status, outboxErrors[id]).then(() => undefined));
}

async function guarded(action: () => Promise<void>) {
  localError.value = "";
  try {
    await action();
  } catch (caught) {
    if (!(caught instanceof Error) || !automationStore.error.value) {
      localError.value = caught instanceof Error ? caught.message : "Не удалось выполнить действие.";
    }
  }
}

function workflowName(id: string) {
  return automationStore.workflows.value.find((item) => item.id === id)?.name ?? id;
}

function dateTime(value: string | null) {
  return value ? new Date(value).toLocaleString("ru-RU") : "—";
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: "Ожидает",
    running: "Выполняется",
    succeeded: "Успешно",
    failed: "Ошибка",
    approved: "Согласовано",
    rejected: "Отклонено",
    sent: "Отправлено",
    sending: "Отправляется",
    cancelled: "Отменено"
  };
  return labels[status] ?? status;
}
</script>

<template>
  <section class="automation-page stack">
    <section class="automation-hero panel">
      <div><p class="eyebrow">Процессы и контроль</p><h2>Автоматизация</h2><p>Триггеры, условия, действия и журнал исполнения.</p></div>
      <div class="hero-actions">
        <button v-if="automationStore.canManageAutomations.value" type="button" :disabled="automationStore.loading.value" @click="runScheduled">Запустить scheduled-проверку</button>
        <button class="secondary" type="button" :disabled="automationStore.loading.value" @click="automationStore.refreshAll">Обновить</button>
      </div>
    </section>

    <p v-if="profileError" class="alert error">{{ profileError }}</p>
    <p v-else-if="denied" class="automation-denied">Роль <code>{{ crmStore.me.value?.role || "не определена" }}</code> не имеет <code>automations:manage</code> или <code>approvals:manage</code>.</p>
    <template v-else>
      <nav class="automation-tabs" aria-label="Разделы автоматизации">
        <button v-for="tab in tabs" :key="tab.id" type="button" :class="{ active: activeTab === tab.id }" @click="activeTab = tab.id">{{ tab.label }}</button>
      </nav>
      <p v-if="automationStore.error.value || localError" class="alert error">{{ localError || automationStore.error.value }}</p>
      <p v-if="automationStore.success.value" class="alert success">{{ automationStore.success.value }}</p>
      <p v-if="scheduledSummary" class="alert info">{{ scheduledSummary }}</p>

      <section v-if="activeTab === 'workflows'">
        <p v-if="!automationStore.canManageAutomations.value" class="automation-denied">Нет права <code>automations:manage</code>.</p>
        <div v-else class="automation-grid">
          <form class="panel automation-form" @submit.prevent="saveWorkflow">
            <header><div><p class="eyebrow">Workflow builder</p><h2>{{ editingWorkflowId ? "Редактирование сценария" : "Новый сценарий" }}</h2></div><button v-if="editingWorkflowId" class="secondary" type="button" @click="resetWorkflow">Отмена</button></header>
            <label>Название<input v-model="workflowForm.name" required minlength="2" /></label>
            <label>Описание<textarea v-model="workflowForm.description" rows="2"></textarea></label>
            <div class="form-pair"><label>Триггер<select v-model="workflowForm.trigger_type"><option v-for="item in triggers" :key="item.value" :value="item.value">{{ item.label }}</option></select></label><label>Приоритет<input v-model.number="workflowForm.priority" type="number" min="0" max="10000" /></label></div>
            <fieldset><legend>Conditions <button class="secondary mini" type="button" @click="addCondition">+ Условие</button></legend><label>Логика<select v-model="workflowForm.condition_logic"><option value="all">Все условия</option><option value="any">Любое условие</option></select></label><div v-for="(condition, index) in workflowForm.conditions" :key="index" class="builder-row condition-row"><input v-model="condition.field" required placeholder="discount_percent" pattern="[a-z][a-z0-9_.]*" /><select v-model="condition.operator"><option v-for="operator in operators" :key="operator" :value="operator">{{ operator }}</option></select><input v-model="condition.value" :disabled="condition.operator === 'is_empty'" placeholder="Значение" /><button class="remove-button" type="button" @click="workflowForm.conditions.splice(index, 1)">×</button></div><p v-if="!workflowForm.conditions.length" class="empty">Без условий — сценарий сработает для каждого события.</p></fieldset>
            <fieldset><legend>Actions <button class="secondary mini" type="button" @click="addAction">+ Действие</button></legend><div v-for="(action, index) in workflowForm.actions" :key="index" class="action-builder"><div class="builder-row"><select v-model="action.type" @change="changeActionType(action)"><option v-for="item in actionTypes" :key="item.value" :value="item.value">{{ item.label }}</option></select><button class="remove-button" type="button" :disabled="workflowForm.actions.length === 1" @click="workflowForm.actions.splice(index, 1)">×</button></div><textarea v-model="action.config" rows="4" required spellcheck="false"></textarea></div></fieldset>
            <label class="check-row"><input v-model="workflowForm.is_active" type="checkbox" />Активировать сразу</label>
            <button type="submit" :disabled="automationStore.loading.value">{{ editingWorkflowId ? "Сохранить изменения" : "Создать сценарий" }}</button>
          </form>
          <section class="panel automation-list"><h2>Сценарии</h2><article v-for="workflow in automationStore.workflows.value" :key="workflow.id" class="automation-card"><div><strong>{{ workflow.name }}</strong><small>{{ triggers.find((item) => item.value === workflow.trigger_type)?.label }} · {{ workflow.conditions.length }} условий · {{ workflow.actions.length }} действий</small><small>Приоритет {{ workflow.priority }} · версия {{ workflow.version }}</small></div><span class="status-pill" :class="{ inactive: !workflow.is_active }">{{ workflow.is_active ? "Активен" : "Отключён" }}</span><div class="card-actions"><button type="button" @click="editWorkflow(workflow)">Редактировать</button><button class="secondary" type="button" @click="toggleWorkflow(workflow)">{{ workflow.is_active ? "Отключить" : "Включить" }}</button></div></article><p v-if="!automationStore.workflows.value.length" class="empty">Сценариев нет.</p></section>
        </div>
      </section>

      <section v-else-if="activeTab === 'templates'">
        <p v-if="!automationStore.canManageAutomations.value" class="automation-denied">Нет права <code>automations:manage</code>.</p>
        <div v-else class="automation-grid">
          <form class="panel automation-form" @submit.prevent="saveTemplate"><header><h2>{{ editingTemplateId ? "Редактирование шаблона" : "Новый шаблон" }}</h2><button v-if="editingTemplateId" class="secondary" type="button" @click="resetTemplate">Отмена</button></header><label>Название<input v-model="templateForm.name" required minlength="2" /></label><label>Канал<input v-model="templateForm.channel" required /></label><label>Тема<input v-model="templateForm.subject" required /></label><label>Тело<textarea v-model="templateForm.body" rows="8" required></textarea></label><button type="submit">{{ editingTemplateId ? "Сохранить" : "Создать шаблон" }}</button></form>
          <section class="panel automation-list"><h2>Шаблоны сообщений</h2><article v-for="item in automationStore.templates.value" :key="item.id" class="automation-card"><div><strong>{{ item.name }}</strong><small>{{ item.channel }} · {{ item.subject }}</small><p>{{ item.body }}</p></div><span class="status-pill" :class="{ inactive: !item.is_active }">{{ item.is_active ? "Активен" : "Отключён" }}</span><div class="card-actions"><button type="button" @click="editTemplate(item)">Редактировать</button><button class="secondary" type="button" @click="toggleTemplate(item)">{{ item.is_active ? "Отключить" : "Включить" }}</button></div></article><p v-if="!automationStore.templates.value.length" class="empty">Шаблонов нет.</p></section>
        </div>
      </section>

      <section v-else-if="activeTab === 'runs'" class="panel automation-list">
        <p v-if="!automationStore.canManageAutomations.value" class="automation-denied">Нет права <code>automations:manage</code>.</p>
        <template v-else><header class="list-head"><div><h2>Журнал запусков</h2><p>Idempotency контролируется backend через event key.</p></div><select v-model="runFilter" @change="automationStore.refreshRuns(runFilter)"><option value="">Все статусы</option><option value="succeeded">Успешно</option><option value="failed">Ошибки</option><option value="running">Выполняется</option></select></header><article v-for="run in automationStore.runs.value" :key="run.id" class="automation-card run-card"><div><strong>{{ workflowName(run.workflow_id) }}</strong><small>{{ run.trigger_type }} · {{ run.entity_type }} · {{ run.entity_id }}</small><small>{{ dateTime(run.started_at) }} · event: {{ run.event_key }}</small><p v-if="run.error" class="run-error">{{ run.error }}</p><details v-if="run.result.length"><summary>Результат действий</summary><pre>{{ JSON.stringify(run.result, null, 2) }}</pre></details></div><span class="status-pill" :class="`status-${run.status}`">{{ statusLabel(run.status) }}</span></article><p v-if="!automationStore.runs.value.length" class="empty">Запусков нет.</p></template>
      </section>

      <section v-else-if="activeTab === 'approvals'" class="panel automation-list">
        <p v-if="!automationStore.canManageApprovals.value" class="automation-denied">Нет права <code>approvals:manage</code>.</p>
        <template v-else><header class="list-head"><div><h2>Согласования</h2><p>Решения продолжают workflow только после approve.</p></div><select v-model="approvalFilter" @change="automationStore.refreshApprovals(approvalFilter)"><option value="">Все статусы</option><option value="pending">Ожидают</option><option value="approved">Согласованы</option><option value="rejected">Отклонены</option></select></header><article v-for="item in automationStore.approvals.value" :key="item.id" class="automation-card approval-card"><div><strong>{{ item.title }}</strong><small>{{ item.entity_type }} · {{ item.entity_id }} · {{ dateTime(item.created_at) }}</small><p v-if="item.reason">{{ item.reason }}</p><p v-if="item.decision_comment">Комментарий: {{ item.decision_comment }}</p><textarea v-if="item.status === 'pending'" v-model="approvalComments[item.id]" rows="2" placeholder="Комментарий к решению"></textarea></div><span class="status-pill" :class="`status-${item.status}`">{{ statusLabel(item.status) }}</span><div v-if="item.status === 'pending'" class="card-actions"><button type="button" @click="decide(item.id, 'approved')">Approve</button><button class="danger-quiet" type="button" @click="decide(item.id, 'rejected')">Reject</button></div></article><p v-if="!automationStore.approvals.value.length" class="empty">Согласований нет.</p></template>
      </section>

      <section v-else class="panel automation-list">
        <p v-if="!automationStore.canManageAutomations.value" class="automation-denied">Нет права <code>automations:manage</code>.</p>
        <template v-else><header class="list-head"><div><h2>Transactional Outbox</h2><p>Подготовленные сообщения и ошибки доставки.</p></div><select v-model="outboxFilter" @change="automationStore.refreshOutbox(outboxFilter)"><option value="">Все статусы</option><option value="pending">Ожидают</option><option value="failed">Ошибки</option><option value="sent">Отправлены</option><option value="cancelled">Отменены</option></select></header><article v-for="item in automationStore.outbox.value" :key="item.id" class="automation-card outbox-card"><div><strong>{{ item.subject }}</strong><small>{{ item.channel }} → {{ item.recipient }} · попыток {{ item.attempts }}</small><p>{{ item.body }}</p><p v-if="item.last_error" class="run-error">{{ item.last_error }}</p><input v-if="['pending','sending','failed'].includes(item.status)" v-model="outboxErrors[item.id]" placeholder="Ошибка для статуса failed" /></div><span class="status-pill" :class="`status-${item.status}`">{{ statusLabel(item.status) }}</span><div v-if="['pending','sending','failed'].includes(item.status)" class="card-actions"><button type="button" @click="markOutbox(item.id, 'sent')">Sent</button><button class="secondary" type="button" @click="markOutbox(item.id, 'failed')">Failed</button><button class="danger-quiet" type="button" @click="markOutbox(item.id, 'cancelled')">Cancel</button></div></article><p v-if="!automationStore.outbox.value.length" class="empty">Outbox пуст.</p></template>
      </section>
    </template>
  </section>
</template>

<style scoped>
.automation-page{padding-bottom:38px}.automation-hero,.automation-form>header,.list-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}.automation-hero h2,.automation-form h2,.automation-list h2{margin:3px 0 6px}.automation-hero p:last-child,.list-head p{margin:0;color:var(--muted)}.hero-actions,.card-actions{display:flex;flex-wrap:wrap;gap:8px}.automation-tabs{display:flex;gap:4px;overflow-x:auto;border:1px solid var(--line);border-radius:10px;padding:4px;background:var(--surface)}.automation-tabs button{min-height:36px;color:var(--muted);background:transparent;white-space:nowrap}.automation-tabs button.active{color:var(--text);background:#fff;box-shadow:0 1px 5px rgb(0 0 0/10%)}.automation-denied{border:1px solid #efc2c2;border-radius:10px;padding:17px;color:#8f2525;background:#fff6f6}.alert.info{color:#24547b;border-color:#bddcf4;background:#eff8ff}.automation-grid{display:grid;grid-template-columns:minmax(330px,430px) minmax(0,1fr);gap:16px;align-items:start}.automation-form{display:grid;gap:13px}.automation-form label{margin:0}.automation-form fieldset{display:grid;gap:9px;border:1px solid var(--line);border-radius:9px;padding:12px}.automation-form legend{padding:0 5px;font-weight:700}.mini{min-height:28px;padding:4px 8px}.form-pair{display:grid;grid-template-columns:1fr 120px;gap:9px}.builder-row{display:grid;grid-template-columns:minmax(0,1fr) minmax(110px,.6fr) auto;gap:7px}.condition-row{grid-template-columns:minmax(110px,1fr) 100px minmax(100px,1fr) auto}.action-builder{display:grid;gap:6px;border-top:1px solid var(--line-soft);padding-top:9px}.remove-button{width:34px;padding:0;color:#9b2929;background:#fff4f4}.check-row{display:flex;align-items:center;gap:8px}.automation-list{display:grid;gap:10px}.automation-card{display:grid;grid-template-columns:minmax(180px,1fr) auto auto;gap:12px;align-items:start;border:1px solid var(--line);border-radius:10px;padding:14px}.automation-card>div:first-child{display:grid;gap:5px}.automation-card small{color:var(--muted)}.automation-card p{margin:2px 0;white-space:pre-wrap}.status-pill{display:inline-flex;border-radius:99px;padding:5px 8px;color:#17663a;background:#e9f8ef;font-size:11px;font-weight:700;white-space:nowrap}.status-pill.inactive,.status-cancelled,.status-rejected{color:#76515b;background:#f3edef}.status-failed{color:#992a2a;background:#fff0f0}.status-pending,.status-running,.status-sending{color:#76500c;background:#fff5d9}.run-error{color:#992a2a!important}.automation-card details{margin-top:5px}.automation-card pre{max-width:100%;overflow:auto;border-radius:8px;padding:9px;background:#f6f8fa;font-size:11px}.danger-quiet{color:#a02929;border-color:#efc2c2;background:#fff6f6}@media(max-width:980px){.automation-grid{grid-template-columns:1fr}.automation-card{grid-template-columns:minmax(0,1fr) auto}.automation-card .card-actions{grid-column:1/-1}}@media(max-width:650px){.automation-hero,.list-head{flex-direction:column}.hero-actions{width:100%}.hero-actions button{flex:1}.form-pair,.builder-row,.condition-row,.automation-card{grid-template-columns:1fr}.automation-card>*{grid-column:1!important}}
</style>
