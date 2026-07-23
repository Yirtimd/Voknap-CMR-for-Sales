import { computed, ref } from "vue";

import { api, apiBlob, emptyToNull, post } from "../api";
import type {
  AgentAction,
  AgentChatResponse,
  AgentHistoryMessage,
  AnalyticsOverview,
  Activity,
  AuthResponse,
  Company,
  CompanyCopilot,
  HomeCopilot,
  CompanyWorkspace,
  CommunicationEvent,
  Contact,
  ConnectorAccount,
  ConnectorDefinition,
  ConnectorSyncRun,
  CsvExportResponse,
  AppliedTemplate,
  CompanyTemplate,
  Deal,
  KnowledgeAskResponse,
  KnowledgeDocument,
  KnowledgeSearchResult,
  Lead,
  Me,
  Note,
  NextAction,
  Pipeline,
  AuditLog,
  FeatureFlag,
  ProductionOverview,
  Task,
  Tenant,
  TenantExport,
  TenantPlan
} from "../types";

const token = ref(localStorage.getItem("cmr_token") ?? "");
const tenantId = ref(localStorage.getItem("cmr_tenant_id") ?? "");
const tenants = ref<Tenant[]>(JSON.parse(localStorage.getItem("cmr_tenants") ?? "[]"));
const error = ref("");
const ok = ref("");
const isLoading = ref(false);

const contacts = ref<Contact[]>([]);
const companies = ref<Company[]>([]);
const companyWorkspace = ref<CompanyWorkspace | null>(null);
const leads = ref<Lead[]>([]);
const pipelines = ref<Pipeline[]>([]);
const deals = ref<Deal[]>([]);
const tasks = ref<Task[]>([]);
const notes = ref<Note[]>([]);
const knowledgeDocuments = ref<KnowledgeDocument[]>([]);
const knowledgeSearchResults = ref<KnowledgeSearchResult[]>([]);
const knowledgeAnswer = ref<KnowledgeAskResponse | null>(null);
const agentHistory = ref<AgentHistoryMessage[]>([]);
const agentActions = ref<AgentAction[]>([]);
const agentLastResponse = ref<AgentChatResponse | null>(null);
const companyCopilot = ref<CompanyCopilot | null>(null);
const homeCopilot = ref<HomeCopilot | null>(null);
const connectorDefinitions = ref<ConnectorDefinition[]>([]);
const connectorAccounts = ref<ConnectorAccount[]>([]);
const connectorRuns = ref<ConnectorSyncRun[]>([]);
const communicationEvents = ref<CommunicationEvent[]>([]);
const csvExport = ref<CsvExportResponse | null>(null);
const companyTemplates = ref<CompanyTemplate[]>([]);
const appliedTemplates = ref<AppliedTemplate[]>([]);
const productionOverview = ref<ProductionOverview | null>(null);
const auditLogs = ref<AuditLog[]>([]);
const featureFlags = ref<FeatureFlag[]>([]);
const tenantPlan = ref<TenantPlan | null>(null);
const tenantExport = ref<TenantExport | null>(null);
const activities = ref<Activity[]>([]);
const analyticsOverview = ref<AnalyticsOverview | null>(null);
const nextActions = ref<NextAction[]>([]);
const me = ref<Me | null>(null);

const registerForm = ref({
  company_name: "Demo Company",
  company_slug: `demo-${Math.floor(Math.random() * 10000)}`,
  owner_email: "owner@example.com",
  owner_full_name: "Demo Owner",
  owner_password: "password123"
});

const loginForm = ref({ email: "owner@example.com", password: "password123" });
const pipelineForm = ref({ name: "Основная воронка", stages: "Новый, В работе, КП, Сделка" });
const contactForm = ref({ company_id: "", name: "Иван Петров", phone: "+79990000000", email: "client@example.com", company_name: "Ромашка" });
const companyForm = ref({ name: "Ромашка", website: "https://example.com", industry: "B2B", description: "Тестовая компания" });
const leadForm = ref({ company_id: "", title: "Заявка с сайта", source: "site", contact_id: "" });
const dealForm = ref({
  company_id: "",
  title: "Первая сделка",
  amount: 50000,
  discount_percent: 0,
  lead_id: "",
  stage_id: "",
  probability: 50,
  expected_close_date: "",
  expected_next_event: "Ответ клиента",
  next_step: "Позвонить клиенту",
  risk_level: "medium",
  forecast_category: "pipeline"
});
const taskForm = ref({
  company_id: "",
  title: "Позвонить клиенту",
  description: "Уточнить потребность",
  deal_id: "",
  priority: "normal",
  due_at: ""
});
const noteForm = ref({ text: "Клиент интересуется внедрением CRM" });
const knowledgeDocumentForm = ref({
  title: "Скрипт продаж",
  source_type: "text",
  text: "Компания продает CRM для отделов продаж. Основная ценность: учет лидов, сделок, задач, база знаний и AI-помощник. Первый шаг после заявки: связаться с клиентом в течение 15 минут, уточнить сферу бизнеса, количество менеджеров и текущую CRM."
});
const knowledgeSearchForm = ref({ query: "Что делать после новой заявки?", limit: 6, scope: "global", include_global: false });
const knowledgeAskForm = ref({ question: "Что делать после новой заявки?", limit: 6 });
const agentForm = ref({ message: "Дай сводку по CRM", company_id: "", deal_id: "" });
const connectorAccountForm = ref({
  connector_code: "csv",
  title: "CSV import/export",
  email_provider: "gmail",
  host: "imap.gmail.com",
  port: 993,
  username: "",
  password: "",
  folder: "INBOX",
  use_ssl: true
});
const csvImportForm = ref({
  account_id: "",
  csv_text: "name,phone,email,company_name,lead_title,source\nИван Петров,+79990000000,client@example.com,Ромашка,Заявка из CSV,csv"
});
const templateApplyForm = ref({
  template_code: "b2b_services",
  include_pipeline: true,
  include_knowledge: true
});
const featureFlagForm = ref({ code: "ai_agent", title: "AI агент", enabled: true });
const planForm = ref({
  plan_code: "trial",
  users_limit: 5,
  leads_limit: 500,
  documents_limit: 50,
  ai_requests_limit: 1000
});
const activityForm = ref({
  company_id: "",
  type: "COMMENT",
  title: "Комментарий",
  description: "Короткая заметка в timeline",
  contact_id: "",
  deal_id: ""
});
const communicationEventForm = ref({
  channel: "email",
  direction: "inbound",
  sender: "client@example.com",
  recipient: "sales@crmsales.app",
  subject: "Новый входящий запрос",
  body: "Клиент просит уточнить стоимость, сроки внедрения и следующий шаг.",
  company_id: "",
  contact_id: "",
  deal_id: ""
});
const nextActionForm = ref({
  company_id: "",
  deal_id: "",
  contact_id: "",
  title: "Связаться с клиентом",
  description: "",
  source: "manual",
  priority: "normal",
  due_at: ""
});

const isAuthed = computed(() => token.value.length > 0 && tenantId.value.length > 0);
const activeTenant = computed(() => tenants.value.find((tenant) => tenant.id === tenantId.value) ?? tenants.value[0]);
const allStages = computed(() => pipelines.value.flatMap((pipeline) => pipeline.stages));
const openTasks = computed(() => tasks.value.filter((task) => !task.done_at));
const totalPipeline = computed(() => deals.value.reduce((sum, deal) => sum + Number(deal.amount ?? 0), 0));
const dealsByStage = computed(() =>
  allStages.value.map((stage) => {
    const stageDeals = deals.value.filter((deal) => deal.stage_id === stage.id);
    return {
      stage,
      deals: stageDeals,
      amount: stageDeals.reduce((sum, deal) => sum + Number(deal.amount ?? 0), 0)
    };
  })
);

async function run(action: () => Promise<void>, success: string) {
  error.value = "";
  ok.value = "";
  isLoading.value = true;
  try {
    await action();
    ok.value = success;
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Unknown error";
  } finally {
    isLoading.value = false;
  }
}

function saveSession(auth: AuthResponse) {
  token.value = auth.access_token;
  tenants.value = auth.tenants;
  const savedTenantId = localStorage.getItem("cmr_tenant_id");
  const preferredTenant =
    auth.tenants.find((tenant) => tenant.id === savedTenantId) ??
    auth.tenants.find((tenant) => tenant.slug === "developer-test") ??
    auth.tenants[0];
  tenantId.value = preferredTenant?.id ?? "";
  localStorage.setItem("cmr_token", token.value);
  localStorage.setItem("cmr_tenant_id", tenantId.value);
  localStorage.setItem("cmr_tenants", JSON.stringify(tenants.value));
}

async function registerCompany() {
  await run(async () => {
    const auth = await api<AuthResponse>("/auth/register-company", post(registerForm.value));
    saveSession(auth);
    await refreshAll();
  }, "Компания создана");
}

async function login() {
  await run(async () => {
    const auth = await api<AuthResponse>("/auth/login", post(loginForm.value));
    saveSession(auth);
    await refreshAll();
  }, "Вход выполнен");
}

function logout() {
  token.value = "";
  tenantId.value = "";
  tenants.value = [];
  contacts.value = [];
  leads.value = [];
  deals.value = [];
  tasks.value = [];
  notes.value = [];
  pipelines.value = [];
  nextActions.value = [];
  homeCopilot.value = null;
  me.value = null;
  localStorage.clear();
}

async function refreshMe() {
  if (!isAuthed.value) return;
  me.value = await api<Me>("/me", {}, token.value, tenantId.value);
}

function saveTenantId() {
  localStorage.setItem("cmr_tenant_id", tenantId.value);
  void refreshAll();
  void refreshMe();
  void refreshCommunication();
}

async function refreshAll() {
  if (!isAuthed.value) return;
  const [companyList, contactList, leadList, pipelineList, dealList, taskList, noteList, nextActionList] = await Promise.all([
    api<Company[]>("/sales/companies", {}, token.value, tenantId.value),
    api<Contact[]>("/sales/contacts", {}, token.value, tenantId.value),
    api<Lead[]>("/sales/leads", {}, token.value, tenantId.value),
    api<Pipeline[]>("/sales/pipelines", {}, token.value, tenantId.value),
    api<Deal[]>("/sales/deals", {}, token.value, tenantId.value),
    api<Task[]>("/sales/tasks", {}, token.value, tenantId.value),
    api<Note[]>("/sales/notes", {}, token.value, tenantId.value),
    api<NextAction[]>("/sales/next-actions", {}, token.value, tenantId.value)
  ]);
  companies.value = companyList;
  const firstCompanyId = companyList[0]?.id ?? "";
  contactForm.value.company_id ||= firstCompanyId;
  leadForm.value.company_id ||= firstCompanyId;
  dealForm.value.company_id ||= firstCompanyId;
  taskForm.value.company_id ||= firstCompanyId;
  activityForm.value.company_id ||= firstCompanyId;
  communicationEventForm.value.company_id ||= firstCompanyId;
  contacts.value = contactList;
  leads.value = leadList;
  pipelines.value = pipelineList;
  deals.value = dealList;
  tasks.value = taskList;
  notes.value = noteList;
  nextActions.value = nextActionList;
  if (!dealForm.value.stage_id && allStages.value[0]) dealForm.value.stage_id = allStages.value[0].id;
}

async function createCompany() {
  await run(async () => {
    const company = await api<Company>("/sales/companies", post(emptyToNull(companyForm.value)), token.value, tenantId.value);
    await refreshAll();
    contactForm.value.company_id = company.id;
    leadForm.value.company_id = company.id;
    dealForm.value.company_id = company.id;
    taskForm.value.company_id = company.id;
    activityForm.value.company_id = company.id;
  }, "Компания создана");
}

async function loadCompanyWorkspace(companyId: string) {
  if (!isAuthed.value) return;
  companyWorkspace.value = await api<CompanyWorkspace>(
    `/sales/companies/${companyId}`,
    {},
    token.value,
    tenantId.value
  );
}

async function refreshCommunication() {
  if (!isAuthed.value) return;
  communicationEvents.value = await api<CommunicationEvent[]>("/communication/events", {}, token.value, tenantId.value);
}

async function createCommunicationEvent() {
  await run(async () => {
    await api<CommunicationEvent>(
      "/communication/events",
      post(emptyToNull(communicationEventForm.value)),
      token.value,
      tenantId.value
    );
    await refreshCommunication();
    await refreshActivities();
  }, "Входящее событие создано");
}

async function linkCommunicationEvent(event: CommunicationEvent) {
  await run(async () => {
    await api<CommunicationEvent>(
      `/communication/events/${event.id}/link`,
      post(
        {
          company_id: event.company_id,
          contact_id: event.contact_id,
          deal_id: event.deal_id
        },
        "PATCH"
      ),
      token.value,
      tenantId.value
    );
    await refreshCommunication();
  }, "Коммуникация привязана");
}

async function createActivityFromCommunication(eventId: string) {
  await run(async () => {
    await api<CommunicationEvent>(
      `/communication/events/${eventId}/activity`,
      post({}),
      token.value,
      tenantId.value
    );
    await refreshCommunication();
    await refreshActivities();
  }, "Activity создана из коммуникации");
}

async function refreshCompanyCopilot(companyId: string) {
  if (!isAuthed.value) return;
  companyCopilot.value = await api<CompanyCopilot>(
    `/ai-agent/companies/${companyId}/copilot`,
    {},
    token.value,
    tenantId.value
  );
  await refreshAgent();
}

async function refreshHomeCopilot() {
  if (!isAuthed.value) return;
  homeCopilot.value = await api<HomeCopilot>(
    "/ai-agent/home/copilot",
    {},
    token.value,
    tenantId.value
  );
}

async function refreshKnowledge() {
  if (!isAuthed.value) return;
  knowledgeDocuments.value = await api<KnowledgeDocument[]>(
    "/knowledge/documents",
    {},
    token.value,
    tenantId.value
  );
}

async function createKnowledgeDocument() {
  await run(async () => {
    await api<KnowledgeDocument>(
      "/knowledge/documents",
      post(knowledgeDocumentForm.value),
      token.value,
      tenantId.value
    );
    await refreshKnowledge();
  }, "Документ добавлен в базу знаний");
}

async function uploadKnowledgeDocument(
  file: File,
  context: {
    title?: string;
    scope?: "global" | "company" | "deal";
    company_id?: string;
    deal_id?: string;
  } = {}
): Promise<boolean> {
  const form = new FormData();
  form.append("file", file);
  form.append("scope", context.scope ?? "global");
  if (context.title?.trim()) form.append("title", context.title.trim());
  if (context.company_id) form.append("company_id", context.company_id);
  if (context.deal_id) form.append("deal_id", context.deal_id);
  let succeeded = false;
  await run(async () => {
    await api<KnowledgeDocument>(
      "/knowledge/documents/upload",
      { method: "POST", body: form },
      token.value,
      tenantId.value
    );
    if ((context.scope ?? "global") === "global") await refreshKnowledge();
    succeeded = true;
  }, "Файл загружен и добавлен в базу знаний");
  return succeeded;
}

async function downloadKnowledgeDocument(document: Pick<KnowledgeDocument, "title" | "download_url">) {
  if (!document.download_url) return;
  await run(async () => {
    const blob = await apiBlob(document.download_url ?? "", token.value, tenantId.value);
    const url = URL.createObjectURL(blob);
    const anchor = window.document.createElement("a");
    anchor.href = url;
    anchor.download = document.title;
    anchor.click();
    URL.revokeObjectURL(url);
  }, "Файл скачан");
}

async function searchKnowledge() {
  await run(async () => {
    knowledgeSearchResults.value = await api<KnowledgeSearchResult[]>(
      "/knowledge/search",
      post(knowledgeSearchForm.value),
      token.value,
      tenantId.value
    );
  }, "Поиск выполнен");
}

async function askKnowledge(context: {
  scope?: "global" | "company" | "deal";
  company_id?: string;
  deal_id?: string;
  include_global?: boolean;
} = {}): Promise<boolean> {
  const payload = emptyToNull({
    ...knowledgeAskForm.value,
    scope: "global",
    include_global: false,
    ...context
  });
  knowledgeAnswer.value = null;
  let succeeded = false;
  await run(async () => {
    knowledgeAnswer.value = await api<KnowledgeAskResponse>(
      "/knowledge/ask",
      post(payload),
      token.value,
      tenantId.value
    );
    succeeded = true;
  }, "Ответ готов");
  return succeeded;
}

async function refreshAgent() {
  if (!isAuthed.value) return;
  const [history, actions] = await Promise.all([
    api<AgentHistoryMessage[]>("/ai-agent/history", {}, token.value, tenantId.value),
    api<AgentAction[]>("/ai-agent/actions", {}, token.value, tenantId.value)
  ]);
  agentHistory.value = history.reverse();
  agentActions.value = actions;
}

async function sendAgentMessage() {
  const payload = emptyToNull({ ...agentForm.value });
  await run(async () => {
    agentLastResponse.value = await api<AgentChatResponse>(
      "/ai-agent/chat",
      post(payload),
      token.value,
      tenantId.value
    );
    await refreshAgent();
  }, "AI агент ответил");
  agentForm.value.company_id = "";
  agentForm.value.deal_id = "";
}

async function confirmAgentAction(actionId: string) {
  await run(async () => {
    await api<AgentAction>(
      `/ai-agent/actions/${actionId}/confirm`,
      post({}),
      token.value,
      tenantId.value
    );
    await refreshAll();
    await refreshAgent();
  }, "Действие выполнено");
}

async function rejectAgentAction(actionId: string) {
  await run(async () => {
    await api<AgentAction>(
      `/ai-agent/actions/${actionId}/reject`,
      post({}),
      token.value,
      tenantId.value
    );
    await refreshAgent();
  }, "Действие отклонено");
}

async function refreshConnectors() {
  if (!isAuthed.value) return;
  const [definitions, accounts, runs] = await Promise.all([
    api<ConnectorDefinition[]>("/connectors/definitions", {}, token.value, tenantId.value),
    api<ConnectorAccount[]>("/connectors/accounts", {}, token.value, tenantId.value),
    api<ConnectorSyncRun[]>("/connectors/runs", {}, token.value, tenantId.value)
  ]);
  connectorDefinitions.value = definitions;
  connectorAccounts.value = accounts;
  connectorRuns.value = runs;
  if (!csvImportForm.value.account_id) {
    const csvAccount = accounts.find((account) => account.connector_code === "csv");
    csvImportForm.value.account_id = csvAccount?.id ?? "";
  }
}

async function createConnectorAccount() {
  await run(async () => {
    const isEmail = connectorAccountForm.value.connector_code === "email";
    await api<ConnectorAccount>(
      "/connectors/accounts",
      post({
        connector_code: connectorAccountForm.value.connector_code,
        title: connectorAccountForm.value.title,
        credentials: isEmail
          ? {
              username: connectorAccountForm.value.username,
              password: connectorAccountForm.value.password
            }
          : {},
        settings: isEmail
          ? {
              host: connectorAccountForm.value.host,
              port: connectorAccountForm.value.port,
              folder: connectorAccountForm.value.folder,
              use_ssl: connectorAccountForm.value.use_ssl,
              starttls: !connectorAccountForm.value.use_ssl,
              sync_limit: 100
            }
          : {}
      }),
      token.value,
      tenantId.value
    );
    connectorAccountForm.value.password = "";
    await refreshConnectors();
  }, "Коннектор подключен");
}

async function syncConnectorAccount(accountId: string) {
  await run(async () => {
    await api<ConnectorSyncRun>(
      `/connectors/accounts/${accountId}/sync`,
      post({ payload: {} }),
      token.value,
      tenantId.value
    );
    await refreshAll();
    await refreshCommunication();
    await refreshConnectors();
  }, "Синхронизация запущена");
}

async function retryConnectorRun(runId: string) {
  await run(async () => {
    await api<ConnectorSyncRun>(
      `/connectors/runs/${runId}/retry`,
      post({}),
      token.value,
      tenantId.value
    );
    await refreshAll();
    await refreshConnectors();
  }, "Retry выполнен");
}

async function importCsv() {
  await run(async () => {
    await api<ConnectorSyncRun>(
      `/connectors/accounts/${csvImportForm.value.account_id}/csv/import`,
      post({ csv_text: csvImportForm.value.csv_text }),
      token.value,
      tenantId.value
    );
    await refreshAll();
    await refreshConnectors();
  }, "CSV импорт выполнен");
}

async function exportCsv() {
  await run(async () => {
    csvExport.value = await api<CsvExportResponse>("/connectors/csv/export", {}, token.value, tenantId.value);
  }, "CSV экспорт готов");
}

async function refreshTemplates() {
  if (!isAuthed.value) return;
  const [templates, applied] = await Promise.all([
    api<CompanyTemplate[]>("/templates", {}, token.value, tenantId.value),
    api<AppliedTemplate[]>("/templates/applied", {}, token.value, tenantId.value)
  ]);
  companyTemplates.value = templates;
  appliedTemplates.value = applied;
  if (!templates.some((template) => template.code === templateApplyForm.value.template_code)) {
    templateApplyForm.value.template_code = templates[0]?.code ?? "";
  }
}

async function applyCompanyTemplate() {
  await run(async () => {
    await api<AppliedTemplate>(
      "/templates/apply",
      post(templateApplyForm.value),
      token.value,
      tenantId.value
    );
    await refreshAll();
    await refreshKnowledge();
    await refreshTemplates();
  }, "Шаблон применен");
}

async function refreshProduction() {
  if (!isAuthed.value) return;
  const [overview, audit, flags, plan] = await Promise.all([
    api<ProductionOverview>("/production/overview", {}, token.value, tenantId.value),
    api<AuditLog[]>("/production/audit", {}, token.value, tenantId.value),
    api<FeatureFlag[]>("/production/flags", {}, token.value, tenantId.value),
    api<TenantPlan>("/production/plan", {}, token.value, tenantId.value)
  ]);
  productionOverview.value = overview;
  auditLogs.value = audit;
  featureFlags.value = flags;
  tenantPlan.value = plan;
  planForm.value = {
    plan_code: plan.plan_code,
    users_limit: plan.users_limit,
    leads_limit: plan.leads_limit,
    documents_limit: plan.documents_limit,
    ai_requests_limit: plan.ai_requests_limit
  };
}

async function createFeatureFlag() {
  await run(async () => {
    await api<FeatureFlag>("/production/flags", post(featureFlagForm.value), token.value, tenantId.value);
    await refreshProduction();
  }, "Feature flag сохранен");
}

async function toggleFeatureFlag(flag: FeatureFlag) {
  await run(async () => {
    await api<FeatureFlag>(
      `/production/flags/${flag.id}`,
      post({ enabled: !flag.enabled }, "PATCH"),
      token.value,
      tenantId.value
    );
    await refreshProduction();
  }, "Feature flag обновлен");
}

async function updateTenantPlan() {
  await run(async () => {
    tenantPlan.value = await api<TenantPlan>(
      "/production/plan",
      post(planForm.value, "PUT"),
      token.value,
      tenantId.value
    );
    await refreshProduction();
  }, "Тариф обновлен");
}

async function createAuditMarker() {
  await run(async () => {
    await api<AuditLog>("/production/audit", post({}), token.value, tenantId.value);
    await refreshProduction();
  }, "Audit marker создан");
}

async function exportTenantData() {
  await run(async () => {
    tenantExport.value = await api<TenantExport>("/production/export", {}, token.value, tenantId.value);
    await refreshProduction();
  }, "Экспорт готов");
}

async function refreshActivities() {
  if (!isAuthed.value) return;
  activities.value = await api<Activity[]>("/activities", {}, token.value, tenantId.value);
}

async function refreshAnalytics() {
  if (!isAuthed.value) return;
  analyticsOverview.value = await api<AnalyticsOverview>(
    "/analytics/overview?forecast_days=90&stuck_days=14&activity_days=30",
    {},
    token.value,
    tenantId.value
  );
}

async function createActivity() {
  await run(async () => {
    await api<Activity>(
      "/activities",
      post({
        type: activityForm.value.type,
        title: activityForm.value.title,
        description: activityForm.value.description,
        company_id: activityForm.value.company_id,
        contact_id: activityForm.value.contact_id || null,
        deal_id: activityForm.value.deal_id || null,
        metadata: { source: "timeline_page" }
      }),
      token.value,
      tenantId.value
    );
    await refreshActivities();
  }, "Activity создана");
}

async function createPipeline() {
  await run(async () => {
    await api<Pipeline>(
      "/sales/pipelines",
      post({
        name: pipelineForm.value.name,
        stages: pipelineForm.value.stages.split(",").map((stage) => stage.trim()).filter(Boolean)
      }),
      token.value,
      tenantId.value
    );
    await refreshAll();
  }, "Воронка создана");
}

async function createContact() {
  await run(async () => {
    await api<Contact>("/sales/contacts", post(emptyToNull(contactForm.value)), token.value, tenantId.value);
    await refreshAll();
  }, "Контакт создан");
}

async function createLead() {
  await run(async () => {
    await api<Lead>("/sales/leads", post(emptyToNull(leadForm.value)), token.value, tenantId.value);
    await refreshAll();
  }, "Лид создан");
}

async function createDeal() {
  await run(async () => {
    await api<Deal>("/sales/deals", post(emptyToNull(dealForm.value)), token.value, tenantId.value);
    await refreshAll();
  }, "Сделка создана");
}

async function moveDeal(deal: Deal, stageId: string) {
  await run(async () => {
    await api<Deal>(
      `/sales/deals/${deal.id}/move`,
      post({ stage_id: stageId, version: deal.version }, "PATCH"),
      token.value,
      tenantId.value
    );
    await refreshAll();
  }, "Сделка перемещена");
}

async function createTask() {
  await run(async () => {
    await api<Task>("/sales/tasks", post(emptyToNull(taskForm.value)), token.value, tenantId.value);
    await refreshAll();
  }, "Задача создана");
}

async function createNextAction(payload: Partial<typeof nextActionForm.value> = {}) {
  await run(async () => {
    const source = { ...nextActionForm.value, ...payload };
    await api<NextAction>(
      "/sales/next-actions",
      post(emptyToNull(source)),
      token.value,
      tenantId.value
    );
    await refreshAll();
    if (source.company_id) await loadCompanyWorkspace(source.company_id);
  }, "Следующее действие сохранено");
}

async function toggleNextAction(action: NextAction, isDone = action.status !== "done") {
  await run(async () => {
    await api<NextAction>(
      `/sales/next-actions/${action.id}/done`,
      post({ is_done: isDone }, "PATCH"),
      token.value,
      tenantId.value
    );
    await refreshAll();
    await loadCompanyWorkspace(action.company_id);
  }, isDone ? "Следующее действие выполнено" : "Следующее действие открыто");
}

async function toggleTask(task: Task) {
  await run(async () => {
    await api<Task>(
      `/sales/tasks/${task.id}/done`,
      post({ is_done: task.done_at === null, version: task.version }, "PATCH"),
      token.value,
      tenantId.value
    );
    await refreshAll();
  }, "Задача обновлена");
}

async function createNote(target: "lead" | "deal", id: string) {
  await run(async () => {
    const companyId =
      target === "lead"
        ? leads.value.find((lead) => lead.id === id)?.company_id
        : deals.value.find((deal) => deal.id === id)?.company_id;
    await api<Note>(
      "/sales/notes",
      post({
        company_id: companyId,
        text: noteForm.value.text,
        lead_id: target === "lead" ? id : null,
        deal_id: target === "deal" ? id : null
      }),
      token.value,
      tenantId.value
    );
    await refreshAll();
  }, "Заметка создана");
}

function money(value: number | null | undefined) {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0
  }).format(value ?? 0);
}

export const crmStore = {
  token,
  tenantId,
  tenants,
  error,
  ok,
  isLoading,
  contacts,
  companies,
  companyWorkspace,
  leads,
  pipelines,
  deals,
  tasks,
  notes,
  knowledgeDocuments,
  knowledgeSearchResults,
  knowledgeAnswer,
  agentHistory,
  agentActions,
  agentLastResponse,
  companyCopilot,
  homeCopilot,
  connectorDefinitions,
  connectorAccounts,
  connectorRuns,
  communicationEvents,
  csvExport,
  companyTemplates,
  appliedTemplates,
  productionOverview,
  auditLogs,
  featureFlags,
  tenantPlan,
  tenantExport,
  activities,
  analyticsOverview,
  nextActions,
  me,
  registerForm,
  loginForm,
  pipelineForm,
  contactForm,
  companyForm,
  leadForm,
  dealForm,
  taskForm,
  noteForm,
  knowledgeDocumentForm,
  knowledgeSearchForm,
  knowledgeAskForm,
  agentForm,
  connectorAccountForm,
  csvImportForm,
  templateApplyForm,
  featureFlagForm,
  planForm,
  activityForm,
  communicationEventForm,
  nextActionForm,
  isAuthed,
  activeTenant,
  allStages,
  openTasks,
  totalPipeline,
  dealsByStage,
  registerCompany,
  login,
  logout,
  saveTenantId,
  refreshMe,
  refreshAll,
  createCompany,
  loadCompanyWorkspace,
  refreshCompanyCopilot,
  refreshHomeCopilot,
  refreshKnowledge,
  refreshAgent,
  refreshConnectors,
  refreshCommunication,
  refreshTemplates,
  refreshProduction,
  refreshActivities,
  refreshAnalytics,
  createPipeline,
  createContact,
  createLead,
  createDeal,
  moveDeal,
  createTask,
  createNextAction,
  toggleNextAction,
  toggleTask,
  createNote,
  createKnowledgeDocument,
  uploadKnowledgeDocument,
  downloadKnowledgeDocument,
  searchKnowledge,
  askKnowledge,
  sendAgentMessage,
  confirmAgentAction,
  rejectAgentAction,
  createConnectorAccount,
  syncConnectorAccount,
  retryConnectorRun,
  createCommunicationEvent,
  linkCommunicationEvent,
  createActivityFromCommunication,
  importCsv,
  exportCsv,
  applyCompanyTemplate,
  createFeatureFlag,
  toggleFeatureFlag,
  updateTenantPlan,
  createAuditMarker,
  exportTenantData,
  createActivity,
  money
};
