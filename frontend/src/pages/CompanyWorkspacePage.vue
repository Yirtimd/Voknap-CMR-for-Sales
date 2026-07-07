<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { api, emptyToNull, post } from "../api";
import AIAssistantPanel from "../components/crm/AIAssistantPanel.vue";
import CompanyCardHeader from "../components/crm/CompanyCardHeader.vue";
import CompanyContacts from "../components/crm/CompanyContacts.vue";
import CompanyCurrentDeal from "../components/crm/CompanyCurrentDeal.vue";
import CompanyNextAction from "../components/crm/CompanyNextAction.vue";
import CompanyTasks from "../components/crm/CompanyTasks.vue";
import CompanyTimeline from "../components/crm/CompanyTimeline.vue";
import type { Activity, Company, Deal, Task } from "../types";
import { crmStore } from "../stores/crm";

const route = useRoute();
const activeTab = ref("overview");
const actionMode = ref<"call" | "meeting" | "note" | "task" | "deal">("call");
const isSaving = ref(false);

const workspace = computed(() => crmStore.companyWorkspace.value);
const companyId = computed(() => String(route.params.id));
const currentDeal = computed(() => workspace.value?.deals[0] ?? null);
const firstContact = computed(() => workspace.value?.contacts[0] ?? null);
const hasPipelineStage = computed(() => Boolean(crmStore.allStages.value[0]));

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

const activityForm = ref({
  title: "Call completed",
  description: "Discussed next step and customer context.",
  contact_id: "",
  deal_id: ""
});

const meetingForm = ref({
  title: "Meeting scheduled",
  description: "Discovery meeting with decision makers.",
  contact_id: "",
  deal_id: ""
});

const noteForm = ref({
  title: "Note added",
  description: "Important customer context.",
  contact_id: "",
  deal_id: ""
});

const taskForm = ref({
  title: "Follow up with customer",
  description: "Confirm next step.",
  deal_id: "",
  priority: "high",
  due_at: ""
});

const dealForm = ref({
  title: "New opportunity",
  amount: 100000,
  stage_id: "",
  probability: 40,
  expected_close_date: "",
  expected_next_event: "Customer response",
  next_step: "Schedule discovery",
  risk_level: "medium",
  forecast_category: "pipeline"
});

const companyEditForm = ref({
  name: "",
  website: "",
  industry: "",
  description: "",
  status: "active",
  company_type: "",
  health_score: 70
});

const changeRows = computed(() =>
  (workspace.value?.activities ?? [])
    .filter((activity) => {
      const changes = activity.metadata?.changes;
      return activity.type === "SYSTEM" && Array.isArray(changes) && changes.length > 0;
    })
    .flatMap((activity) => {
      const changes = activity.metadata.changes as Array<{ field: string; old: unknown; new: unknown }>;
      return changes.map((change) => ({ activity, change }));
    })
);

onMounted(async () => {
  await loadWorkspace();
});

watch(workspace, (value) => {
  if (!value) return;
  activityForm.value.contact_id = value.contacts[0]?.id ?? "";
  activityForm.value.deal_id = value.deals[0]?.id ?? "";
  meetingForm.value.contact_id = value.contacts[0]?.id ?? "";
  meetingForm.value.deal_id = value.deals[0]?.id ?? "";
  noteForm.value.contact_id = value.contacts[0]?.id ?? "";
  noteForm.value.deal_id = value.deals[0]?.id ?? "";
  taskForm.value.deal_id = value.deals[0]?.id ?? "";
  dealForm.value.stage_id ||= crmStore.allStages.value[0]?.id ?? "";
  companyEditForm.value = {
    name: value.company.name,
    website: value.company.website ?? "",
    industry: value.company.industry ?? "",
    description: value.company.description ?? "",
    status: value.company.status,
    company_type: value.company.company_type ?? "",
    health_score: value.company.health_score ?? value.health.score ?? 70
  };
}, { immediate: true });

async function loadWorkspace() {
  await crmStore.refreshAll();
  await crmStore.loadCompanyWorkspace(companyId.value);
}

async function runWorkspaceAction(action: () => Promise<void>) {
  if (!workspace.value) return;
  isSaving.value = true;
  crmStore.error.value = "";
  crmStore.ok.value = "";
  try {
    await action();
    await loadWorkspace();
    crmStore.ok.value = "Company workspace updated";
  } catch (caught) {
    crmStore.error.value = caught instanceof Error ? caught.message : "Unknown error";
  } finally {
    isSaving.value = false;
  }
}

async function createActivity(type: string, channel: string, form: typeof activityForm.value) {
  await api<Activity>(
    "/activities",
    post({
      company_id: companyId.value,
      contact_id: form.contact_id || null,
      deal_id: form.deal_id || null,
      type,
      channel,
      title: form.title,
      description: form.description,
      metadata: { source: "company_workspace_quick_action" }
    }),
    crmStore.token.value,
    crmStore.tenantId.value
  );
}

function submitCall() {
  void runWorkspaceAction(() => createActivity("CALL", "Call", activityForm.value));
}

function submitMeeting() {
  void runWorkspaceAction(() => createActivity("MEETING", "Meeting", meetingForm.value));
}

function submitNote() {
  void runWorkspaceAction(() => createActivity("COMMENT", "Message", noteForm.value));
}

function submitTask() {
  void runWorkspaceAction(async () => {
    await api<Task>(
      "/sales/tasks",
      post(emptyToNull({
        company_id: companyId.value,
        title: taskForm.value.title,
        description: taskForm.value.description,
        deal_id: taskForm.value.deal_id,
        priority: taskForm.value.priority,
        due_at: taskForm.value.due_at
      })),
      crmStore.token.value,
      crmStore.tenantId.value
    );
  });
}

function submitDeal() {
  void runWorkspaceAction(async () => {
    await api<Deal>(
      "/sales/deals",
      post(emptyToNull({
        company_id: companyId.value,
        title: dealForm.value.title,
        amount: dealForm.value.amount,
        stage_id: dealForm.value.stage_id,
        probability: dealForm.value.probability,
        expected_close_date: dealForm.value.expected_close_date,
        expected_next_event: dealForm.value.expected_next_event,
        next_step: dealForm.value.next_step,
        risk_level: dealForm.value.risk_level,
        forecast_category: dealForm.value.forecast_category
      })),
      crmStore.token.value,
      crmStore.tenantId.value
    );
  });
}

function submitCompanyChanges() {
  void runWorkspaceAction(async () => {
    await api<Company>(
      `/sales/companies/${companyId.value}`,
      post(emptyToNull(companyEditForm.value), "PATCH"),
      crmStore.token.value,
      crmStore.tenantId.value
    );
  });
}

function completeTask(task: Task) {
  void runWorkspaceAction(async () => {
    await api<Task>(
      `/sales/tasks/${task.id}/done`,
      post({ is_done: task.done_at === null }, "PATCH"),
      crmStore.token.value,
      crmStore.tenantId.value
    );
  });
}

function formatDate(value?: string | null) {
  if (!value) return "Not set";
  return new Date(value).toLocaleDateString("ru-RU");
}

function formatDateTime(value?: string | null) {
  if (!value) return "Not set";
  return new Date(value).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
}

function fieldLabel(value: string) {
  return value.replace(/_/g, " ");
}
</script>

<template>
  <section v-if="workspace" class="company-workspace-v2">
    <CompanyCardHeader :workspace="workspace" />

    <section class="workspace-action-bar">
      <div class="quick-actions">
        <button type="button" :class="{ active: actionMode === 'call' }" @click="actionMode = 'call'">Call</button>
        <button type="button" :class="{ active: actionMode === 'meeting' }" @click="actionMode = 'meeting'">Meeting</button>
        <button type="button" :class="{ active: actionMode === 'note' }" @click="actionMode = 'note'">Note</button>
        <button type="button" :class="{ active: actionMode === 'task' }" @click="actionMode = 'task'">Task</button>
        <button type="button" :class="{ active: actionMode === 'deal' }" @click="actionMode = 'deal'">Deal</button>
      </div>

      <form v-if="actionMode === 'call'" class="quick-action-form" @submit.prevent="submitCall">
        <select v-model="activityForm.contact_id">
          <option value="">No contact</option>
          <option v-for="contact in workspace.contacts" :key="contact.id" :value="contact.id">{{ contact.name }}</option>
        </select>
        <select v-model="activityForm.deal_id">
          <option value="">No deal</option>
          <option v-for="deal in workspace.deals" :key="deal.id" :value="deal.id">{{ deal.title }}</option>
        </select>
        <input v-model="activityForm.title" />
        <input v-model="activityForm.description" />
        <button type="submit" :disabled="isSaving">Save call</button>
      </form>

      <form v-else-if="actionMode === 'meeting'" class="quick-action-form" @submit.prevent="submitMeeting">
        <select v-model="meetingForm.contact_id">
          <option value="">No contact</option>
          <option v-for="contact in workspace.contacts" :key="contact.id" :value="contact.id">{{ contact.name }}</option>
        </select>
        <select v-model="meetingForm.deal_id">
          <option value="">No deal</option>
          <option v-for="deal in workspace.deals" :key="deal.id" :value="deal.id">{{ deal.title }}</option>
        </select>
        <input v-model="meetingForm.title" />
        <input v-model="meetingForm.description" />
        <button type="submit" :disabled="isSaving">Save meeting</button>
      </form>

      <form v-else-if="actionMode === 'note'" class="quick-action-form" @submit.prevent="submitNote">
        <select v-model="noteForm.contact_id">
          <option value="">No contact</option>
          <option v-for="contact in workspace.contacts" :key="contact.id" :value="contact.id">{{ contact.name }}</option>
        </select>
        <select v-model="noteForm.deal_id">
          <option value="">No deal</option>
          <option v-for="deal in workspace.deals" :key="deal.id" :value="deal.id">{{ deal.title }}</option>
        </select>
        <input v-model="noteForm.title" />
        <input v-model="noteForm.description" />
        <button type="submit" :disabled="isSaving">Save note</button>
      </form>

      <form v-else-if="actionMode === 'task'" class="quick-action-form" @submit.prevent="submitTask">
        <select v-model="taskForm.deal_id">
          <option value="">No deal</option>
          <option v-for="deal in workspace.deals" :key="deal.id" :value="deal.id">{{ deal.title }}</option>
        </select>
        <input v-model="taskForm.title" />
        <select v-model="taskForm.priority">
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
        <input v-model="taskForm.due_at" type="datetime-local" />
        <button type="submit" :disabled="isSaving">Create task</button>
      </form>

      <form v-else class="quick-action-form" @submit.prevent="submitDeal">
        <input v-model="dealForm.title" />
        <input v-model.number="dealForm.amount" type="number" />
        <select v-model="dealForm.stage_id" required>
          <option value="">Select stage</option>
          <option v-for="stage in crmStore.allStages.value" :key="stage.id" :value="stage.id">{{ stage.name }}</option>
        </select>
        <input v-model.number="dealForm.probability" type="number" min="0" max="100" />
        <button type="submit" :disabled="isSaving || !hasPipelineStage">Create deal</button>
      </form>
    </section>

    <nav class="company-tabs workspace-tabs" aria-label="Company workspace sections">
      <button
        v-for="tab in tabs"
        :key="tab.code"
        type="button"
        :class="{ active: activeTab === tab.code }"
        @click="activeTab = tab.code"
      >{{ tab.label }}</button>
    </nav>

    <section v-if="activeTab === 'overview'" class="workspace-modal-grid">
      <div class="workspace-primary">
        <section class="section-grid">
          <CompanyNextAction :workspace="workspace" />
          <CompanyCurrentDeal :workspace="workspace" />
          <section class="panel">
            <h2>AI Summary</h2>
            <p class="answer-text">{{ workspace.ai_summary }}</p>
          </section>
          <section class="panel">
            <h2>AI Insights</h2>
            <article v-for="insight in workspace.ai_insights" :key="insight" class="list-row">
              <span>{{ insight }}</span>
            </article>
            <p v-if="!workspace.ai_insights.length" class="empty">No insights yet</p>
          </section>
        </section>
      </div>
      <aside class="workspace-rail">
        <AIAssistantPanel title="Company AI" preset="What should we do with this company next?" />
        <section class="panel compact-panel">
          <h2>Health</h2>
          <div class="metric-mini"><span>Score</span><strong>{{ workspace.health.score ?? workspace.company.health_score ?? 0 }}</strong></div>
          <div class="metric-mini"><span>Risk</span><strong>{{ workspace.health.risk_level ?? "not set" }}</strong></div>
          <div class="metric-mini"><span>Success</span><strong>{{ workspace.health.success_chance ?? 0 }}%</strong></div>
        </section>
      </aside>
    </section>

    <section v-else-if="activeTab === 'timeline'" class="workspace-modal-grid">
      <div class="workspace-primary">
        <CompanyTimeline :workspace="workspace" />
      </div>
      <aside class="workspace-rail">
        <section class="panel compact-panel">
          <h2>Activity Feed</h2>
          <article v-for="activity in workspace.activities" :key="activity.id" class="feed-row">
            <span class="timeline-icon">{{ activity.type.slice(0, 2) }}</span>
            <div>
              <strong>{{ activity.title }}</strong>
              <small>{{ activity.channel ?? activity.type }} · {{ formatDateTime(activity.created_at) }}</small>
            </div>
          </article>
        </section>
      </aside>
    </section>

    <section v-else-if="activeTab === 'contacts'" class="section-grid">
      <CompanyContacts :workspace="workspace" />
      <section class="panel">
        <h2>Contact Actions</h2>
        <article v-for="contact in workspace.contacts" :key="contact.id" class="list-row">
          <span>{{ contact.name }}</span>
          <small>{{ contact.phone ?? contact.email ?? "No contact channel" }}</small>
        </article>
      </section>
    </section>

    <section v-else-if="activeTab === 'deals'" class="section-grid">
      <CompanyCurrentDeal :workspace="workspace" />
      <section class="panel">
        <h2>All Deals</h2>
        <article v-for="deal in workspace.deals" :key="deal.id" class="entity-row">
          <div>
            <strong>{{ deal.title }}</strong>
            <small>{{ deal.risk_level ?? "risk not set" }} · {{ deal.forecast_category ?? "pipeline" }} · close {{ formatDate(deal.expected_close_date) }}</small>
          </div>
          <span>{{ crmStore.money(deal.amount) }}</span>
        </article>
      </section>
    </section>

    <section v-else-if="activeTab === 'tasks'" class="section-grid">
      <CompanyTasks :workspace="workspace" />
      <section class="panel">
        <h2>Execution Queue</h2>
        <article v-for="task in workspace.tasks" :key="task.id" class="entity-row">
          <div>
            <strong :class="{ done: task.done_at }">{{ task.title }}</strong>
            <small>{{ task.priority }} · {{ task.status }} · {{ formatDateTime(task.due_at) }}</small>
          </div>
          <button class="secondary" type="button" @click="completeTask(task)">{{ task.done_at ? "Reopen" : "Done" }}</button>
        </article>
      </section>
    </section>

    <section v-else-if="activeTab === 'files'" class="section-grid">
      <section class="panel wide">
        <h2>Files</h2>
        <article v-for="file in workspace.files" :key="file.id" class="entity-row">
          <div>
            <strong>{{ file.name }}</strong>
            <small>{{ file.file_type ?? "file" }} · {{ file.mime_type ?? "unknown" }}</small>
          </div>
          <a class="button-link secondary-link" :href="file.download_url">Open</a>
        </article>
        <p v-if="!workspace.files.length" class="empty">No files yet</p>
      </section>
    </section>

    <section v-else-if="activeTab === 'knowledge'" class="section-grid">
      <section class="panel">
        <h2>Company Knowledge</h2>
        <p class="hint">Company-specific RAG layer will attach files, notes, calls, and deal context here.</p>
      </section>
      <section class="panel">
        <h2>Ask Knowledge</h2>
        <label>Question<textarea v-model="crmStore.knowledgeAskForm.value.question"></textarea></label>
        <button type="button" @click="crmStore.askKnowledge">Ask</button>
        <p v-if="crmStore.knowledgeAnswer.value" class="answer-text">{{ crmStore.knowledgeAnswer.value.answer }}</p>
      </section>
    </section>

    <section v-else class="workspace-modal-grid">
      <div class="workspace-primary">
        <section class="panel">
          <h2>Change History</h2>
          <article v-for="row in changeRows" :key="`${row.activity.id}-${row.change.field}`" class="history-change-row">
            <span>{{ fieldLabel(row.change.field) }}</span>
            <div>
              <strong>{{ row.change.old ?? "empty" }}</strong>
              <small>changed to</small>
              <strong>{{ row.change.new ?? "empty" }}</strong>
            </div>
            <small>{{ formatDateTime(row.activity.created_at) }}</small>
          </article>
          <p v-if="!changeRows.length" class="empty">No tracked field changes yet</p>
        </section>
      </div>
      <aside class="workspace-rail">
        <form class="panel compact-panel" @submit.prevent="submitCompanyChanges">
          <h2>Edit Company</h2>
          <label>Name<input v-model="companyEditForm.name" /></label>
          <label>Website<input v-model="companyEditForm.website" /></label>
          <label>Industry<input v-model="companyEditForm.industry" /></label>
          <label>Status
            <select v-model="companyEditForm.status">
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="archived">Archived</option>
            </select>
          </label>
          <label>Health<input v-model.number="companyEditForm.health_score" type="number" min="0" max="100" /></label>
          <label>Description<textarea v-model="companyEditForm.description"></textarea></label>
          <button type="submit" :disabled="isSaving">Save changes</button>
        </form>
      </aside>
    </section>
  </section>
</template>
