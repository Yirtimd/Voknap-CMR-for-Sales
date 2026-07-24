import { computed, ref } from "vue";

import { api, apiErrorMessage, post } from "../api";
import type {
  ApprovalHistory,
  ApprovalRequest,
  AutomationAction,
  AutomationCondition,
  AutomationMessageTemplate,
  AutomationOutboxItem,
  AutomationRun,
  AutomationTriggerType,
  AutomationWorkflow,
  ScheduledAutomationResult
} from "../types";
import { crmStore } from "./crm";

const workflows = ref<AutomationWorkflow[]>([]);
const templates = ref<AutomationMessageTemplate[]>([]);
const runs = ref<AutomationRun[]>([]);
const approvals = ref<ApprovalRequest[]>([]);
const approvalHistory = ref<Record<string, ApprovalHistory[]>>({});
const outbox = ref<AutomationOutboxItem[]>([]);
const loading = ref(false);
const error = ref("");
const success = ref("");

const permissions = computed(() => new Set(crmStore.me.value?.permissions ?? []));
const role = computed(() => crmStore.me.value?.role);
const canManageAutomations = computed(() =>
  permissions.value.has("automations:manage") || ["owner", "admin", "sales_manager"].includes(role.value ?? "")
);
const canManageApprovals = computed(() =>
  permissions.value.has("approvals:manage") || ["owner", "admin", "sales_manager"].includes(role.value ?? "")
);
const canOpen = computed(() => canManageAutomations.value || canManageApprovals.value);

function auth() {
  return [crmStore.token.value, crmStore.tenantId.value] as const;
}

async function refreshWorkflows() {
  if (!canManageAutomations.value) return void (workflows.value = []);
  workflows.value = await api<AutomationWorkflow[]>("/automations/workflows", {}, ...auth());
}

async function refreshTemplates() {
  if (!canManageAutomations.value) return void (templates.value = []);
  templates.value = await api<AutomationMessageTemplate[]>("/automations/templates", {}, ...auth());
}

async function refreshRuns(status?: string) {
  if (!canManageAutomations.value) return void (runs.value = []);
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  runs.value = await api<AutomationRun[]>(`/automations/runs${query}`, {}, ...auth());
}

async function refreshApprovals(status?: string) {
  if (!canManageApprovals.value) return void (approvals.value = []);
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  approvals.value = await api<ApprovalRequest[]>(`/automations/approvals${query}`, {}, ...auth());
}

async function refreshApprovalHistory(id: string) {
  const rows = await api<ApprovalHistory[]>(`/automations/approvals/${id}/history`, {}, ...auth());
  approvalHistory.value = { ...approvalHistory.value, [id]: rows };
  return rows;
}

async function refreshOutbox(status?: string) {
  if (!canManageAutomations.value) return void (outbox.value = []);
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  outbox.value = await api<AutomationOutboxItem[]>(`/automations/outbox${query}`, {}, ...auth());
}

async function refreshAll() {
  loading.value = true;
  error.value = "";
  try {
    await Promise.all([
      refreshWorkflows(),
      refreshTemplates(),
      refreshRuns(),
      refreshApprovals(),
      refreshOutbox()
    ]);
  } catch (caught) {
    error.value = errorMessage(caught);
  } finally {
    loading.value = false;
  }
}

type WorkflowPayload = {
  name: string;
  description?: string | null;
  trigger_type: AutomationTriggerType;
  conditions: AutomationCondition[];
  condition_logic: "all" | "any";
  actions: AutomationAction[];
  priority: number;
  is_active: boolean;
};

async function createWorkflow(payload: WorkflowPayload) {
  return mutate(async () => {
    const result = await api<AutomationWorkflow>("/automations/workflows", post(payload), ...auth());
    await refreshWorkflows();
    return result;
  }, "Сценарий создан");
}

async function updateWorkflow(id: string, version: number, payload: Partial<WorkflowPayload>) {
  return mutate(async () => {
    const result = await api<AutomationWorkflow>(
      `/automations/workflows/${id}`,
      post({ version, ...payload }, "PATCH"),
      ...auth()
    );
    await refreshWorkflows();
    return result;
  }, "Сценарий обновлён");
}

async function createTemplate(payload: { name: string; channel: string; subject: string; body: string }) {
  return mutate(async () => {
    const result = await api<AutomationMessageTemplate>("/automations/templates", post(payload), ...auth());
    await refreshTemplates();
    return result;
  }, "Шаблон создан");
}

async function updateTemplate(
  id: string,
  payload: Partial<Pick<AutomationMessageTemplate, "name" | "channel" | "subject" | "body" | "is_active">>
) {
  return mutate(async () => {
    const result = await api<AutomationMessageTemplate>(
      `/automations/templates/${id}`,
      post(payload, "PATCH"),
      ...auth()
    );
    await refreshTemplates();
    return result;
  }, "Шаблон обновлён");
}

async function runScheduled() {
  return mutate(async () => {
    const result = await api<ScheduledAutomationResult>("/automations/run-scheduled", post({}), ...auth());
    await refreshRuns();
    return result;
  }, "Scheduled-проверка завершена");
}

async function decideApproval(
  id: string,
  version: number,
  decision: "approved" | "rejected",
  comment?: string | null
) {
  return mutate(async () => {
    const result = await api<ApprovalRequest>(
      `/automations/approvals/${id}/decision`,
      post({ version, decision, comment: comment || null }),
      ...auth()
    );
    await Promise.all([refreshApprovals(), canManageAutomations.value ? refreshRuns() : Promise.resolve()]);
    return result;
  }, decision === "approved" ? "Согласование подтверждено" : "Согласование отклонено");
}

async function reassignApproval(id: string, version: number, assignedToId: string, comment?: string | null) {
  return mutate(async () => {
    const result = await api<ApprovalRequest>(
      `/automations/approvals/${id}/reassign`,
      post({ version, assigned_to_id: assignedToId, comment: comment || null }),
      ...auth()
    );
    await refreshApprovals();
    return result;
  }, "Согласование переназначено");
}

async function cancelApproval(id: string, version: number, comment: string) {
  return mutate(async () => {
    const result = await api<ApprovalRequest>(
      `/automations/approvals/${id}/cancel`,
      post({ version, comment }),
      ...auth()
    );
    await Promise.all([refreshApprovals(), canManageAutomations.value ? refreshRuns() : Promise.resolve()]);
    return result;
  }, "Согласование отменено");
}

async function updateOutbox(
  id: string,
  status: "sent" | "failed" | "cancelled",
  errorDetail?: string | null
) {
  return mutate(async () => {
    const result = await api<AutomationOutboxItem>(
      `/automations/outbox/${id}`,
      post({ status, error: errorDetail || null }, "PATCH"),
      ...auth()
    );
    await refreshOutbox();
    return result;
  }, "Статус Outbox обновлён");
}

async function mutate<T>(action: () => Promise<T>, message: string): Promise<T> {
  loading.value = true;
  error.value = "";
  success.value = "";
  try {
    const result = await action();
    success.value = message;
    return result;
  } catch (caught) {
    error.value = errorMessage(caught);
    throw caught;
  } finally {
    loading.value = false;
  }
}

function errorMessage(caught: unknown) {
  return apiErrorMessage(caught, "Неизвестная ошибка");
}

function clearMessages() {
  error.value = "";
  success.value = "";
}

export const automationStore = {
  workflows,
  templates,
  runs,
  approvals,
  approvalHistory,
  outbox,
  loading,
  error,
  success,
  canManageAutomations,
  canManageApprovals,
  canOpen,
  refreshWorkflows,
  refreshTemplates,
  refreshRuns,
  refreshApprovals,
  refreshApprovalHistory,
  refreshOutbox,
  refreshAll,
  createWorkflow,
  updateWorkflow,
  createTemplate,
  updateTemplate,
  runScheduled,
  decideApproval,
  reassignApproval,
  cancelApproval,
  updateOutbox,
  clearMessages
};
