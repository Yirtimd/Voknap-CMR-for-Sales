<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import type { Deal } from "../types";
import { crmStore } from "../stores/crm";
import { formatStageName } from "../utils/stages";

const route = useRoute();
const router = useRouter();
const mode = ref<"kanban" | "table" | "list" | "forecast">("kanban");
const selectedDeal = ref<Deal | null>(null);
const showCreateDeal = ref(false);
const search = ref("");
const filters = ref({ stage: "", owner: "", company: "", minAmount: 0, risk: "", minScore: 0 });
const viewSaved = ref(false);
const showMoreMenu = ref(false);
const showNextActionMenu = ref(false);
const showAllTimeline = ref(false);
const showAllFiles = ref(false);
const draggedDealId = ref("");
const dragOverStageId = ref("");
const didDrag = ref(false);

const modes = [
  { code: "kanban", label: "Kanban" },
  { code: "table", label: "Table" },
  { code: "list", label: "List" },
  { code: "forecast", label: "Forecast" }
] as const;

const visibleDeals = computed(() => {
  const query = search.value.trim().toLowerCase();
  return crmStore.deals.value.filter((deal) =>
    (!query || [deal.title, companyName(deal.company_id), deal.next_step, deal.expected_next_event]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query))) &&
    (!filters.value.stage || deal.stage_id === filters.value.stage) &&
    (!filters.value.owner || deal.owner_id === filters.value.owner) &&
    (!filters.value.company || deal.company_id === filters.value.company) &&
    Number(deal.amount ?? 0) >= filters.value.minAmount &&
    (!filters.value.risk || deal.risk_level === filters.value.risk) &&
    aiScore(deal) >= filters.value.minScore
  );
});

const ownerIds = computed(() => [...new Set(crmStore.deals.value.map((deal) => deal.owner_id).filter(Boolean))] as string[]);

const columns = computed(() =>
  crmStore.allStages.value.map((stage) => {
    const deals = visibleDeals.value.filter((deal) => deal.stage_id === stage.id);
    return {
      stage,
      deals,
      amount: deals.reduce((sum, deal) => sum + Number(deal.amount ?? 0), 0)
    };
  })
);

const forecast = computed(() =>
  columns.value.map((column, index) => ({
    ...column,
    probability: Math.max(20, 80 - index * 15),
    weighted: column.amount * (Math.max(20, 80 - index * 15) / 100)
  }))
);

const openDeals = computed(() => crmStore.deals.value.filter((deal) => deal.status !== "won" && deal.status !== "lost"));
const wonDeals = computed(() => crmStore.deals.value.filter((deal) => deal.status === "won"));
const lostDeals = computed(() => crmStore.deals.value.filter((deal) => deal.status === "lost"));
const atRiskDeals = computed(() => openDeals.value.filter((deal) => aiScore(deal) < 45 || deal.risk_level === "high"));
const likelyDeal = computed(() =>
  [...openDeals.value].sort((left, right) => aiScore(right) - aiScore(left))[0] ?? crmStore.deals.value[0]
);
const forecastAmount = computed(() =>
  openDeals.value.reduce((sum, deal) => sum + Number(deal.amount ?? 0) * (aiScore(deal) / 100), 0)
);
const riskAmount = computed(() => atRiskDeals.value.reduce((sum, deal) => sum + Number(deal.amount ?? 0), 0));

const kpis = computed(() => [
  { label: "Pipeline", value: crmStore.money(crmStore.totalPipeline.value), delta: "+12%" },
  { label: "Open Deals", value: String(openDeals.value.length), delta: "24 active" },
  { label: "Won", value: String(wonDeals.value.length), delta: "42% win rate" },
  { label: "Lost", value: String(lostDeals.value.length), delta: "needs review" },
  { label: "Forecast", value: crmStore.money(forecastAmount.value), delta: "AI weighted" }
]);

function companyName(companyId: string) {
  return crmStore.companies.value.find((company) => company.id === companyId)?.name ?? "Company";
}

function stageIndex(stageId: string) {
  return Math.max(0, crmStore.allStages.value.findIndex((stage) => stage.id === stageId));
}

function stageName(stageId: string) {
  const stage = crmStore.allStages.value.find((item) => item.id === stageId);
  return formatStageName(stage?.name ?? stageId);
}

function aiScore(deal: Deal) {
  if (typeof deal.probability === "number") return Math.min(98, Math.max(8, deal.probability));
  const total = Math.max(1, crmStore.allStages.value.length);
  const stageScore = Math.round(((stageIndex(deal.stage_id) + 1) / total) * 78);
  const taskBonus = openTasks(deal).length > 0 ? 6 : -5;
  const riskPenalty = deal.risk_level === "high" ? 28 : deal.risk_level === "medium" ? 12 : 0;
  const amountSignal = Number(deal.amount ?? 0) > 300000 ? 4 : 0;
  return Math.min(97, Math.max(18, stageScore + taskBonus + amountSignal - riskPenalty));
}

function scoreTone(deal: Deal) {
  const score = aiScore(deal);
  if (score < 45 || deal.risk_level === "high") return "risk";
  if (score >= 75) return "hot";
  return "steady";
}

function openTasks(deal: Deal) {
  return crmStore.tasks.value.filter((task) => task.deal_id === deal.id && !task.done_at);
}

function dealTasks(deal: Deal) {
  return crmStore.tasks.value.filter((task) => task.deal_id === deal.id);
}

function completedTasks(deal: Deal) {
  return dealTasks(deal).filter((task) => task.done_at);
}

function taskProgress(deal: Deal) {
  const tasks = dealTasks(deal);
  if (tasks.length === 0) return 0;
  return Math.round((completedTasks(deal).length / tasks.length) * 100);
}

function notesForDeal(deal: Deal) {
  return crmStore.notes.value.filter((note) => note.deal_id === deal.id);
}

function documentsForDeal(deal: Deal) {
  return crmStore.knowledgeDocuments.value.filter(
    (document) => document.deal_id === deal.id || document.company_id === deal.company_id
  );
}

function nextAction(deal: Deal) {
  const action = crmStore.nextActions.value.find(
    (item) => item.deal_id === deal.id && item.status === "open"
  );
  if (action) return action.title;
  return deal.next_step || openTasks(deal)[0]?.title || deal.expected_next_event || "Call client";
}

function completeSelectedNextAction() {
  if (!selectedDeal.value) return;
  const action = crmStore.nextActions.value.find(
    (item) => item.deal_id === selectedDeal.value?.id && item.status === "open"
  );
  if (action) {
    void crmStore.toggleNextAction(action, true);
    return;
  }
  const task = openTasks(selectedDeal.value)[0];
  if (task) void crmStore.toggleTask(task);
}

function saveView() {
  localStorage.setItem("cmr_deals_view", JSON.stringify({ filters: filters.value, mode: mode.value }));
  viewSaved.value = true;
  crmStore.ok.value = "Deals view saved";
}

async function copyDealLink() {
  if (!selectedDeal.value) return;
  await navigator.clipboard.writeText(`${window.location.origin}/deals?deal=${selectedDeal.value.id}`);
  crmStore.ok.value = "Deal link copied";
}

async function copyDealSummary() {
  if (!selectedDeal.value) return;
  await navigator.clipboard.writeText(`${selectedDeal.value.title}\n${companyName(selectedDeal.value.company_id)}\n${crmStore.money(selectedDeal.value.amount)}\n${nextAction(selectedDeal.value)}`);
  crmStore.ok.value = "Deal summary copied";
}

function openSelectedCompany() {
  if (!selectedDeal.value) return;
  const companyId = selectedDeal.value.company_id;
  showMoreMenu.value = false;
  showNextActionMenu.value = false;
  selectedDeal.value = null;
  void router.push(`/companies?company=${companyId}`);
}

function dueLabel(deal: Deal) {
  const task = openTasks(deal)[0];
  if (task?.due_at) return new Date(task.due_at).toLocaleDateString("en", { month: "short", day: "numeric" });
  return deal.expected_close_date ? "Close " + new Date(deal.expected_close_date).toLocaleDateString("en", { month: "short", day: "numeric" }) : "Today";
}

function dateLabel(value?: string | null) {
  if (!value) return "Not set";
  return new Date(value).toLocaleDateString("en", { month: "short", day: "numeric", year: "numeric" });
}

function aiReasons(deal: Deal) {
  const reasons = [];
  if (deal.risk_level === "high") reasons.push("High risk signal in pipeline");
  if (openTasks(deal).length === 0) reasons.push("No active next task");
  if (!deal.expected_close_date) reasons.push("Close date is not confirmed");
  if (aiScore(deal) < 55) reasons.push("Probability needs recovery");
  if (reasons.length === 0) reasons.push("Stage, next action and task coverage look aligned");
  return reasons;
}

function timelineItems(deal: Deal) {
  return [
    ...crmStore.activities.value.filter((activity) => activity.deal_id === deal.id).map((activity) => ({ id: `activity-${activity.id}`, title: activity.title, meta: activity.created_at ? dateLabel(activity.created_at) : activity.type, tone: "base" })),
    ...dealTasks(deal).map((task) => ({
      id: `task-${task.id}`,
      title: task.done_at ? `${task.title} completed` : task.title,
      meta: task.done_at ? dateLabel(task.done_at) : task.due_at ? `Due ${dateLabel(task.due_at)}` : "Task",
      tone: task.done_at ? "done" : "open"
    })),
    ...notesForDeal(deal).map((note) => ({
      id: `note-${note.id}`,
      title: "Note added",
      meta: note.created_at ? dateLabel(note.created_at) : note.text,
      tone: "note"
    })),
    {
      id: `deal-${deal.id}`,
      title: "Deal created",
      meta: deal.created_at ? dateLabel(deal.created_at) : companyName(deal.company_id),
      tone: "base"
    }
  ];
}

function openDeal(deal: Deal) {
  if (didDrag.value) return;
  selectedDeal.value = deal;
}

function onDealDragStart(deal: Deal, event: DragEvent) {
  draggedDealId.value = deal.id;
  dragOverStageId.value = deal.stage_id;
  didDrag.value = true;
  event.dataTransfer?.setData("text/plain", deal.id);
  if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
}

function onDealDragOver(stageId: string, event: DragEvent) {
  if (!draggedDealId.value) return;
  event.preventDefault();
  dragOverStageId.value = stageId;
  if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
}

function onDealDragLeave(stageId: string, event: DragEvent) {
  const nextTarget = event.relatedTarget as Node | null;
  if (nextTarget && (event.currentTarget as HTMLElement).contains(nextTarget)) return;
  if (dragOverStageId.value === stageId) dragOverStageId.value = "";
}

function onDealDrop(stageId: string, event: DragEvent) {
  event.preventDefault();
  const dealId = event.dataTransfer?.getData("text/plain") || draggedDealId.value;
  const deal = crmStore.deals.value.find((item) => item.id === dealId);
  if (deal && deal.stage_id !== stageId) void crmStore.moveDeal(deal, stageId);
  dragOverStageId.value = "";
  draggedDealId.value = "";
}

function onDealDragEnd() {
  dragOverStageId.value = "";
  draggedDealId.value = "";
  window.setTimeout(() => {
    didDrag.value = false;
  }, 0);
}

async function createDealFromModal() {
  await crmStore.createDeal();
  showCreateDeal.value = false;
}

onMounted(async () => {
  const saved = localStorage.getItem("cmr_deals_view");
  if (saved) {
    try {
      const parsed = JSON.parse(saved) as { filters?: typeof filters.value; mode?: typeof mode.value };
      if (parsed.filters) filters.value = parsed.filters;
      if (parsed.mode) mode.value = parsed.mode;
      viewSaved.value = true;
    } catch { localStorage.removeItem("cmr_deals_view"); }
  }
  await Promise.allSettled([crmStore.refreshKnowledge(), crmStore.refreshActivities()]);
});

watch(selectedDeal, () => {
  showMoreMenu.value = false;
  showNextActionMenu.value = false;
  showAllTimeline.value = false;
  showAllFiles.value = false;
});

watch(
  [() => route.query.deal, () => route.query.create, () => crmStore.deals.value.length],
  ([dealId, create]) => {
    if (create === "1") showCreateDeal.value = true;
    if (typeof dealId !== "string") return;
    selectedDeal.value = crmStore.deals.value.find((deal) => deal.id === dealId) ?? selectedDeal.value;
  },
  { immediate: true }
);
</script>

<template>
  <section class="deals-workspace">
    <header class="deals-command">
      <div>
        <h1>Deals</h1>
        <p>AI-prioritized sales pipeline with next actions in view.</p>
      </div>
      <div class="deals-command-actions">
        <label class="deal-search" aria-label="Search deals">
          <span>Search</span>
          <input v-model="search" placeholder="Search..." />
        </label>
        <button type="button" @click="showCreateDeal = true">+ New Deal</button>
        <button class="secondary" type="button" @click="selectedDeal = likelyDeal">AI Overview</button>
      </div>
    </header>

    <section class="deals-kpi-strip">
      <article v-for="item in kpis" :key="item.label" class="deal-kpi">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.delta }}</small>
      </article>
      <article class="deal-kpi danger">
        <span>At risk</span>
        <strong>{{ atRiskDeals.length }}</strong>
        <small>{{ crmStore.money(riskAmount) }} exposed</small>
      </article>
    </section>

    <section class="ai-overview-panel">
      <strong>AI Overview</strong>
      <span>{{ atRiskDeals.length }} deals require attention.</span>
      <span>You may lose {{ crmStore.money(riskAmount) }} if next actions slip today.</span>
      <span v-if="likelyDeal">Most likely: {{ likelyDeal.title }} ({{ aiScore(likelyDeal) }}%).</span>
    </section>

    <section class="deals-filter-bar">
      <div class="deal-filter-controls">
        <span class="filter-label">Filters</span>
        <select v-model="filters.stage" class="filter-chip"><option value="">Все этапы</option><option v-for="stage in crmStore.allStages.value" :key="stage.id" :value="stage.id">{{ stageName(stage.id) }}</option></select>
        <select v-model="filters.owner" class="filter-chip"><option value="">All owners</option><option v-for="ownerId in ownerIds" :key="ownerId" :value="ownerId">{{ ownerId.slice(0, 8) }}</option></select>
        <select v-model="filters.company" class="filter-chip"><option value="">All companies</option><option v-for="company in crmStore.companies.value" :key="company.id" :value="company.id">{{ company.name }}</option></select>
        <label class="filter-chip numeric-filter">Amount ≥<input v-model.number="filters.minAmount" type="number" min="0" /></label>
        <select v-model="filters.risk" class="filter-chip"><option value="">All tags</option><option value="high">High risk</option><option value="medium">Medium risk</option><option value="low">Low risk</option></select>
        <label class="filter-chip numeric-filter">AI ≥<input v-model.number="filters.minScore" type="number" min="0" max="100" /></label>
      </div>
      <button class="secondary save-view-button" type="button" @click="saveView">{{ viewSaved ? "View Saved" : "Save View" }}</button>
    </section>

    <div class="deals-view-row">
      <div class="mode-tabs">
        <button
          v-for="item in modes"
          :key="item.code"
          type="button"
          :class="{ active: mode === item.code }"
          @click="mode = item.code"
        >{{ item.label }}</button>
      </div>
    </div>

    <div v-if="mode === 'kanban'" class="kanban deals-kanban">
      <section
        v-for="column in columns"
        :key="column.stage.id"
        class="kanban-column deal-stage"
        :class="{ 'drag-over': dragOverStageId === column.stage.id && draggedDealId }"
        @dragover="onDealDragOver(column.stage.id, $event)"
        @dragleave="onDealDragLeave(column.stage.id, $event)"
        @drop="onDealDrop(column.stage.id, $event)"
      >
        <header>
          <div>
            <strong>{{ stageName(column.stage.id) }}</strong>
            <small>{{ column.deals.length }} · {{ crmStore.money(column.amount) }}</small>
          </div>
        </header>
        <article
          v-for="deal in column.deals"
          :key="deal.id"
          class="deal-card rich-deal-card"
          :class="[scoreTone(deal), { dragging: draggedDealId === deal.id }]"
          draggable="true"
          @click="openDeal(deal)"
          @dragstart="onDealDragStart(deal, $event)"
          @dragend="onDealDragEnd"
        >
          <div class="deal-card-topline">
            <div>
              <strong>{{ deal.title }}</strong>
              <small>{{ companyName(deal.company_id) }}</small>
            </div>
            <span class="ai-score">{{ scoreTone(deal) === "risk" ? "⚠" : "🔥" }} {{ aiScore(deal) }}%</span>
          </div>
          <div class="deal-amount">{{ crmStore.money(deal.amount) }}</div>
          <div class="next-action-box">
            <span>{{ dueLabel(deal) }}</span>
            <strong>{{ nextAction(deal) }}</strong>
          </div>
          <dl class="deal-facts">
            <div><dt>Owner</dt><dd>Dmitry</dd></div>
            <div><dt>Tasks</dt><dd>{{ openTasks(deal).length }} open</dd></div>
          </dl>
          <div class="progress-line deal-health"><span :style="{ width: `${aiScore(deal)}%` }"></span></div>
        </article>
        <button class="secondary stage-new" type="button" @click="showCreateDeal = true">+ New</button>
      </section>
    </div>

    <section v-else-if="mode === 'table'" class="panel">
      <table class="data-table">
        <thead><tr><th>Deal</th><th>Company</th><th>Stage</th><th>Amount</th><th>AI Score</th><th>Next</th></tr></thead>
        <tbody>
          <tr v-for="deal in visibleDeals" :key="deal.id" @click="selectedDeal = deal">
            <td>{{ deal.title }}</td>
            <td>{{ companyName(deal.company_id) }}</td>
            <td>{{ stageName(deal.stage_id) }}</td>
            <td>{{ crmStore.money(deal.amount) }}</td>
            <td>{{ aiScore(deal) }}%</td>
            <td>{{ nextAction(deal) }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-else-if="mode === 'list'" class="panel">
      <article v-for="deal in visibleDeals" :key="deal.id" class="entity-row" @click="selectedDeal = deal">
        <div>
          <strong>{{ deal.title }}</strong>
          <small>{{ companyName(deal.company_id) }} · {{ aiScore(deal) }}% AI score · {{ nextAction(deal) }}</small>
        </div>
        <span>{{ crmStore.money(deal.amount) }}</span>
      </article>
    </section>

    <section v-else class="panel">
      <h2>Forecast</h2>
      <article v-for="row in forecast" :key="row.stage.id" class="list-row">
        <span>{{ stageName(row.stage.id) }} · {{ row.probability }}%</span>
        <small>{{ crmStore.money(row.weighted) }}</small>
      </article>
    </section>

    <div v-if="selectedDeal" class="deal-modal-backdrop" @click.self="selectedDeal = null">
      <section class="deal-modal-card" role="dialog" aria-modal="true" aria-label="Deal card">
        <header class="deal-modal-header">
          <div class="deal-title-block">
            <p class="eyebrow">Deal</p>
            <h2>{{ selectedDeal.title }}</h2>
            <div class="deal-company-line">
              <span>{{ companyName(selectedDeal.company_id) }}</span>
              <span>{{ selectedDeal.status }}</span>
              <span>{{ selectedDeal.forecast_category ?? "Pipeline" }}</span>
            </div>
          </div>
          <div class="deal-window-actions">
            <button class="secondary icon-button" type="button" title="Link" @click="copyDealLink">↗</button>
            <button class="secondary icon-button" type="button" title="Copy" @click="copyDealSummary">⧉</button>
            <div class="deal-more-wrap">
              <button class="secondary icon-button" type="button" title="More" @click="showMoreMenu = !showMoreMenu">•••</button>
              <section v-if="showMoreMenu" class="deal-more-menu"><button type="button" @click="openSelectedCompany">Open company</button><button type="button" @click="crmStore.createNote('deal', selectedDeal.id); showMoreMenu = false">Add note</button><button type="button" @click="completeSelectedNextAction(); showMoreMenu = false">Complete next action</button></section>
            </div>
            <button class="secondary icon-button" type="button" title="Close" @click="selectedDeal = null">×</button>
          </div>
        </header>

        <section class="deal-hero-metrics">
          <article>
            <span>Amount</span>
            <strong>{{ crmStore.money(selectedDeal.amount) }}</strong>
            <small>Expected income: {{ crmStore.money(Number(selectedDeal.amount ?? 0) * aiScore(selectedDeal) / 100) }}</small>
          </article>
          <article>
            <span>Close probability</span>
            <strong>{{ aiScore(selectedDeal) }}%</strong>
            <small :class="{ positive: aiScore(selectedDeal) >= 60, negative: aiScore(selectedDeal) < 45 }">
              {{ aiScore(selectedDeal) >= 60 ? "Stable signal" : "Needs attention" }}
            </small>
          </article>
          <article>
            <span>Stage</span>
            <strong>{{ stageName(selectedDeal.stage_id) }}</strong>
            <div class="stage-scale" aria-hidden="true">
              <i
                v-for="stage in crmStore.allStages.value"
                :key="stage.id"
                :class="{ active: stageIndex(stage.id) <= stageIndex(selectedDeal.stage_id) }"
              ></i>
            </div>
            <small>Expected close: {{ dateLabel(selectedDeal.expected_close_date) }}</small>
          </article>
        </section>

        <section class="deal-ai-insight-card">
          <div>
            <h3>AI deal assessment</h3>
            <p>Chance to win: <strong>{{ aiScore(selectedDeal) >= 70 ? "High" : aiScore(selectedDeal) >= 45 ? "Medium" : "Low" }}</strong></p>
            <ul>
              <li v-for="reason in aiReasons(selectedDeal)" :key="reason">{{ reason }}</li>
            </ul>
          </div>
          <div>
            <h3>What can increase the chance</h3>
            <ul class="positive-list">
              <li>Confirm budget and decision path</li>
              <li>{{ nextAction(selectedDeal) }}</li>
            </ul>
          </div>
        </section>

        <section class="next-action-panel">
          <div>
            <p class="eyebrow">Next action</p>
            <strong>{{ nextAction(selectedDeal) }}</strong>
            <small>Due: {{ dueLabel(selectedDeal) }}</small>
          </div>
          <button
            type="button"
            :disabled="!crmStore.nextActions.value.some((item) => item.deal_id === selectedDeal?.id && item.status === 'open') && !openTasks(selectedDeal).length"
            @click="completeSelectedNextAction"
          >Complete</button>
          <div class="deal-more-wrap">
            <button class="secondary icon-button" type="button" title="More" @click="showNextActionMenu = !showNextActionMenu">⌄</button>
            <section v-if="showNextActionMenu" class="deal-more-menu"><button type="button" @click="crmStore.createNote('deal', selectedDeal.id); showNextActionMenu = false">Add note</button><button type="button" @click="openSelectedCompany">Open company</button><button type="button" @click="completeSelectedNextAction(); showNextActionMenu = false">Complete</button></section>
          </div>
        </section>

        <dl class="deal-context-strip">
          <div><dt>Owner</dt><dd><span class="avatar-mini">D</span> Dmitry</dd></div>
          <div><dt>Source</dt><dd>Website</dd></div>
          <div><dt>Created</dt><dd>{{ dateLabel(selectedDeal.created_at) }}</dd></div>
          <div><dt>Last activity</dt><dd>{{ timelineItems(selectedDeal)[0]?.meta ?? "No activity" }}</dd></div>
          <div><dt>Deal type</dt><dd>{{ selectedDeal.lead_id ? "New business" : "Direct deal" }}</dd></div>
        </dl>

        <section class="deal-section-card">
          <header>
            <h3>Tasks <span>({{ completedTasks(selectedDeal).length }} of {{ dealTasks(selectedDeal).length }})</span></h3>
            <div class="task-ring" :style="{ '--progress': `${taskProgress(selectedDeal)}%` }">{{ taskProgress(selectedDeal) }}%</div>
          </header>
          <div v-if="dealTasks(selectedDeal).length" class="deal-task-list">
            <label v-for="task in dealTasks(selectedDeal)" :key="task.id" :class="{ done: task.done_at }">
              <input type="checkbox" :checked="Boolean(task.done_at)" disabled />
              <span>
                <strong>{{ task.title }}</strong>
                <small>{{ task.due_at ? `Due ${dateLabel(task.due_at)}` : task.priority }}</small>
              </span>
            </label>
          </div>
          <p v-else class="empty">No tasks yet. Add a next step to keep the deal moving.</p>
        </section>

        <section class="deal-section-card">
          <header>
            <h3>Timeline</h3>
            <button class="secondary text-button" type="button" @click="showAllTimeline = !showAllTimeline">{{ showAllTimeline ? "Collapse" : "View all" }}</button>
          </header>
          <ol class="deal-timeline">
            <li v-for="item in (showAllTimeline ? timelineItems(selectedDeal) : timelineItems(selectedDeal).slice(0, 5))" :key="item.id" :class="item.tone">
              <span></span>
              <div>
                <strong>{{ item.title }}</strong>
                <small>{{ item.meta }}</small>
              </div>
            </li>
          </ol>
        </section>

        <section class="deal-bottom-grid">
          <article class="deal-section-card">
            <header>
              <h3>Notes</h3>
              <button class="secondary text-button" type="button" @click="crmStore.createNote('deal', selectedDeal.id)">Add</button>
            </header>
            <div v-if="notesForDeal(selectedDeal).length" class="note-preview">
              <strong>Latest note</strong>
              <p>{{ notesForDeal(selectedDeal)[0].text }}</p>
              <small>{{ dateLabel(notesForDeal(selectedDeal)[0].created_at) }}</small>
            </div>
            <p v-else class="empty">No notes attached to this deal.</p>
          </article>

          <article class="deal-section-card">
            <header>
              <h3>Files</h3>
              <button class="secondary text-button" type="button" @click="showAllFiles = !showAllFiles">{{ showAllFiles ? "Collapse" : "View all" }}</button>
            </header>
            <div v-if="documentsForDeal(selectedDeal).length" class="file-list">
              <div v-for="document in (showAllFiles ? documentsForDeal(selectedDeal) : documentsForDeal(selectedDeal).slice(0, 2))" :key="document.id">
                <span>▣</span>
                <div>
                  <strong>{{ document.title }}</strong>
                  <small>{{ document.source_type }} · {{ document.status }}</small>
                </div>
              </div>
            </div>
            <p v-else class="empty">No files linked yet.</p>
          </article>
        </section>
      </section>
    </div>

    <div v-if="showCreateDeal" class="workspace-modal-backdrop" @click.self="showCreateDeal = false">
      <section class="deal-create-modal panel">
        <header>
          <div>
            <p class="eyebrow">New Deal</p>
            <h2>Create deal</h2>
          </div>
          <button class="secondary" type="button" @click="showCreateDeal = false">Close</button>
        </header>
        <form class="compact-form" @submit.prevent="createDealFromModal">
          <label>Company
            <select v-model="crmStore.dealForm.value.company_id" required>
              <option value="">Choose</option>
              <option v-for="company in crmStore.companies.value" :key="company.id" :value="company.id">{{ company.name }}</option>
            </select>
          </label>
          <label>Deal<input v-model="crmStore.dealForm.value.title" /></label>
          <label>Amount<input v-model.number="crmStore.dealForm.value.amount" type="number" /></label>
          <label>Lead
            <select v-model="crmStore.dealForm.value.lead_id">
              <option value="">No lead</option>
              <option
                v-for="lead in crmStore.leads.value.filter((item) => item.company_id === crmStore.dealForm.value.company_id)"
                :key="lead.id"
                :value="lead.id"
              >{{ lead.title }}</option>
            </select>
          </label>
          <label>Stage
            <select v-model="crmStore.dealForm.value.stage_id" required>
              <option value="">Choose</option>
              <option v-for="stage in crmStore.allStages.value" :key="stage.id" :value="stage.id">{{ stageName(stage.id) }}</option>
            </select>
          </label>
          <label>Next action<input v-model="crmStore.dealForm.value.next_step" /></label>
          <button type="submit">Create</button>
        </form>
      </section>
    </div>
  </section>
</template>
