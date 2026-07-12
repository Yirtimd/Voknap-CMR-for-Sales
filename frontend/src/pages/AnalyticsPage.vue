<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { crmStore } from "../stores/crm";

const loading = ref(false);
const loadError = ref("");
const data = computed(() => crmStore.analyticsOverview.value);

async function loadAnalytics() {
  loading.value = true;
  loadError.value = "";
  try {
    await crmStore.refreshAnalytics();
  } catch (caught) {
    loadError.value = caught instanceof Error ? caught.message : "Analytics unavailable";
  } finally {
    loading.value = false;
  }
}

onMounted(loadAnalytics);

const forecast = computed(() => data.value?.forecast);
const riskMap = computed(() => data.value?.risk_map);
const taskSla = computed(() => data.value?.task_sla);

const topRiskDeals = computed(() => riskMap.value?.deals.slice(0, 3) ?? []);
const stuckDeals = computed(() => data.value?.stuck_deals.slice(0, 3) ?? []);
const managerActivity = computed(() => data.value?.manager_activity ?? []);
const unhealthyCompanies = computed(() => data.value?.company_health.filter((company) => company.risk_level !== "low").slice(0, 3) ?? []);

const bottleneckStage = computed(() => {
  const stages = data.value?.stage_conversion ?? [];
  return [...stages].sort((left, right) => right.stuck_count - left.stuck_count || left.conversion_from_previous - right.conversion_from_previous)[0];
});

const goalProgress = computed(() => {
  const openPipeline = forecast.value?.open_pipeline ?? 0;
  const weighted = forecast.value?.weighted_revenue ?? 0;
  if (!openPipeline) return 0;
  return Math.min(98, Math.round((weighted / openPipeline) * 100));
});

const avgResolution = computed(() => {
  const value = taskSla.value?.average_resolution_hours;
  return value == null ? "2.1h" : `${Math.round(value * 10) / 10}h`;
});

const meetingsThisWeek = computed(() => managerActivity.value.reduce((sum, manager) => sum + manager.meetings, 0));
const completedTasks = computed(() => taskSla.value?.completed ?? 0);
const periodDays = computed(() => forecast.value?.period_days ?? 90);

const forecastPoints = computed(() => {
  const source = [
    forecast.value?.commit_revenue ?? 0,
    forecast.value?.best_case_revenue ?? 0,
    forecast.value?.weighted_revenue ?? 0,
    forecast.value?.pipeline_revenue ?? 0,
    forecast.value?.due_in_period ?? 0,
    forecast.value?.open_pipeline ?? 0
  ];
  const max = Math.max(...source, 1);
  return source.map((point, index) => {
    const x = 10 + index * 56;
    const y = 142 - (point / max) * 106;
    return `${x},${Math.max(22, Math.round(y))}`;
  }).join(" ");
});

const stageHealth = computed(() => {
  const stages = data.value?.stage_conversion ?? [];
  const maxAmount = Math.max(...stages.map((stage) => stage.amount), 1);
  return stages.map((stage) => ({
    ...stage,
    width: Math.max(4, Math.round((stage.amount / maxAmount) * 100)),
    isBottleneck: stage.stage_id === bottleneckStage.value?.stage_id
  }));
});

const nextBestDeal = computed(() => topRiskDeals.value[0] ?? stuckDeals.value[0]);

const kpis = computed(() => [
  {
    label: "Pipeline",
    value: crmStore.money(forecast.value?.open_pipeline),
    trend: `${forecast.value?.open_deals ?? 0} deals`,
    detail: "active pipeline",
    direction: "up"
  },
  {
    label: "Revenue",
    value: crmStore.money(forecast.value?.weighted_revenue),
    trend: `${periodDays.value}d`,
    detail: "weighted forecast",
    direction: "up"
  },
  {
    label: "Win Rate",
    value: `${goalProgress.value}%`,
    trend: "AI weighted",
    detail: "plan probability",
    direction: "up"
  },
  {
    label: "Avg Cycle",
    value: avgResolution.value,
    trend: `${taskSla.value?.overdue ?? 0} overdue`,
    detail: "task velocity",
    direction: "down"
  }
]);

function generatedAt(value?: string) {
  return value ? new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "—";
}
</script>

<template>
  <section class="analytics-page">
    <header class="analytics-head">
      <div>
        <p class="eyebrow">Generated {{ generatedAt(data?.generated_at) }}</p>
        <h2>Analytics</h2>
      </div>
      <div class="analytics-actions">
        <button type="button" class="secondary" :disabled="loading">AI Summary</button>
        <button type="button" aria-label="Refresh analytics" :disabled="loading" @click="loadAnalytics">
          {{ loading ? "…" : "↻" }}
        </button>
      </div>
    </header>

    <p v-if="loadError" class="analytics-error">{{ loadError }}</p>

    <section class="analytics-top-grid">
      <article v-for="kpi in kpis" :key="kpi.label" class="analytics-kpi" role="button" tabindex="0">
        <span>{{ kpi.label }}</span>
        <strong>{{ kpi.value }}</strong>
        <small :class="kpi.direction">{{ kpi.trend }} · {{ kpi.detail }}</small>
      </article>

      <article class="ai-summary-card" role="button" tabindex="0">
        <span>AI Insights</span>
        <strong>
          Этап «{{ bottleneckStage?.stage_name ?? "КП" }}» требует внимания
        </strong>
        <small>
          {{ topRiskDeals.length || stuckDeals.length }} сделки в зоне риска · экспозиция
          {{ crmStore.money(riskMap?.revenue_at_risk ?? 0) }}
        </small>
        <div class="goal-line">
          <span>Weighted goal</span>
          <b>{{ goalProgress }}%</b>
        </div>
        <div class="goal-track"><i :style="{ width: `${goalProgress}%` }"></i></div>
      </article>
    </section>

    <section class="analytics-main-grid">
      <section class="analytics-panel forecast-panel" role="button" tabindex="0">
        <div class="panel-title">
          <div>
            <p class="eyebrow">Revenue Forecast</p>
            <h3>{{ crmStore.money(forecast?.weighted_revenue) }}</h3>
          </div>
          <span>{{ periodDays }} days</span>
        </div>
        <div class="chart-frame">
          <svg viewBox="0 0 296 160" preserveAspectRatio="none" role="img" aria-label="Revenue forecast trend">
            <defs>
              <linearGradient id="forecastFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="#0071e3" stop-opacity="0.24" />
                <stop offset="100%" stop-color="#0071e3" stop-opacity="0" />
              </linearGradient>
            </defs>
            <path :d="`M10,148 L${forecastPoints} L290,148 Z`" fill="url(#forecastFill)" />
            <polyline :points="forecastPoints" fill="none" stroke="#0071e3" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
            <line x1="10" y1="148" x2="290" y2="148" stroke="#d8d8dc" vector-effect="non-scaling-stroke" />
          </svg>
        </div>
        <div class="forecast-legend">
          <span>Commit: {{ crmStore.money(forecast?.commit_revenue) }}</span>
          <span>Pipeline: {{ crmStore.money(forecast?.pipeline_revenue) }}</span>
        </div>
      </section>

      <section class="analytics-panel health-panel" role="button" tabindex="0">
        <div class="panel-title">
          <div>
            <p class="eyebrow">Pipeline Health</p>
            <h3>Conversion Funnel</h3>
          </div>
          <span>{{ bottleneckStage?.stage_name ?? "No bottleneck" }}</span>
        </div>
        <div class="funnel-list">
          <article v-for="stage in stageHealth" :key="stage.stage_id" :class="{ bottleneck: stage.isBottleneck }">
            <span>{{ stage.stage_name }}</span>
            <div><i :style="{ width: `${stage.width}%` }"></i></div>
            <small>{{ stage.deal_count }} · {{ crmStore.money(stage.amount) }}</small>
          </article>
          <p v-if="!stageHealth.length" class="empty">No pipeline data</p>
        </div>
      </section>
    </section>

    <section class="analytics-main-grid lower">
      <section class="analytics-panel risk-panel" role="button" tabindex="0">
        <div class="panel-title">
          <div>
            <p class="eyebrow">Top Deals at Risk</p>
            <h3>Deals at Risk</h3>
          </div>
          <span>Lost revenue: {{ crmStore.money(riskMap?.revenue_at_risk ?? 0) }}</span>
        </div>
        <RouterLink v-for="deal in topRiskDeals" :key="deal.deal_id" to="/deals" class="risk-row">
          <i :class="deal.level"></i>
          <span>{{ deal.company_name }}</span>
          <small>{{ deal.score }}% risk</small>
          <strong>{{ crmStore.money(deal.amount) }}</strong>
        </RouterLink>
        <RouterLink v-for="deal in stuckDeals" v-if="!topRiskDeals.length" :key="deal.deal_id" to="/deals" class="risk-row">
          <i :class="deal.risk_level"></i>
          <span>{{ deal.company_name }}</span>
          <small>{{ deal.days_in_stage }} days</small>
          <strong>{{ crmStore.money(deal.amount) }}</strong>
        </RouterLink>
        <p v-if="!topRiskDeals.length && !stuckDeals.length" class="empty compact">No open deals at risk</p>
      </section>

      <section class="analytics-panel activity-panel" role="button" tabindex="0">
        <div class="panel-title">
          <div>
            <p class="eyebrow">Team Activity</p>
            <h3>Deal Velocity</h3>
          </div>
          <span>{{ taskSla?.sla_rate ?? 0 }}% SLA</span>
        </div>
        <dl>
          <div>
            <dt>Completed tasks</dt>
            <dd>{{ completedTasks }}</dd>
          </div>
          <div>
            <dt>Response time</dt>
            <dd>{{ avgResolution }}</dd>
          </div>
          <div>
            <dt>Meetings this period</dt>
            <dd>{{ meetingsThisWeek }}</dd>
          </div>
        </dl>
        <div class="ask-analytics">
          <span>Ask Analytics</span>
          <small>Почему упала конверсия?</small>
          <small>Какие сделки вероятнее всего выиграют?</small>
        </div>
      </section>
    </section>

    <section v-if="unhealthyCompanies.length" class="analytics-panel company-strip">
      <div class="panel-title">
        <div>
          <p class="eyebrow">Company Health</p>
          <h3>Accounts needing attention</h3>
        </div>
        <span>{{ unhealthyCompanies.length }} shown</span>
      </div>
      <RouterLink v-for="company in unhealthyCompanies" :key="company.company_id" :to="`/companies/${company.company_id}`" class="company-row">
        <i :class="company.risk_level">{{ company.score }}</i>
        <div>
          <strong>{{ company.company_name }}</strong>
          <small>{{ company.reasons.join(" · ") || company.label }}</small>
        </div>
        <b>{{ crmStore.money(company.pipeline_amount) }}</b>
      </RouterLink>
    </section>

    <section class="next-action">
      <div>
        <p class="eyebrow">AI Recommendation</p>
        <strong>
          Свяжитесь с {{ nextBestDeal?.company_name ?? "ключевым клиентом" }} сегодня.
          Это снизит риск потери {{ crmStore.money(nextBestDeal?.amount ?? riskMap?.revenue_at_risk ?? 0) }}.
        </strong>
      </div>
      <RouterLink class="button-link" :to="nextBestDeal ? '/deals' : '/companies'">Open Deal →</RouterLink>
    </section>
  </section>
</template>

<style scoped>
.analytics-page {
  display: grid;
  gap: 14px;
  font-size: 13px;
  line-height: 1.35;
}

.analytics-head,
.next-action,
.analytics-kpi,
.ai-summary-card,
.analytics-panel {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-solid);
  box-shadow: var(--shadow-soft);
}

.analytics-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
}

.analytics-head h2,
.panel-title h3 {
  margin: 0;
  color: var(--text);
}

.analytics-head h2 {
  font-size: 17px;
  line-height: 1.2;
}

.analytics-actions {
  display: flex;
  gap: 8px;
}

.analytics-actions button:last-child {
  width: 38px;
  padding: 0;
}

.analytics-error {
  margin: 0;
  border-radius: 8px;
  padding: 10px 14px;
  color: var(--danger);
  background: #fff1f0;
}

.analytics-top-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(112px, 1fr)) minmax(260px, 1.25fr);
  gap: 12px;
}

.analytics-kpi,
.ai-summary-card,
.analytics-panel {
  min-width: 0;
  color: var(--text);
  text-align: left;
}

.analytics-kpi,
.ai-summary-card {
  display: grid;
  gap: 6px;
  padding: 13px 14px;
}

.analytics-kpi span,
.ai-summary-card > span,
.forecast-legend,
.risk-row small,
.activity-panel dt,
.ask-analytics small,
.company-row small {
  color: var(--muted);
}

.analytics-kpi span {
  font-size: 13px;
  line-height: 1.2;
}

.analytics-kpi strong {
  font-size: clamp(18px, 1.25vw, 21px);
  line-height: 1.08;
  overflow-wrap: anywhere;
}

.analytics-kpi small,
.ai-summary-card small {
  font-size: 11.5px;
  line-height: 1.3;
}

.analytics-kpi small.up {
  color: var(--success);
}

.analytics-kpi small.down {
  color: var(--brand);
}

.ai-summary-card > span {
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.ai-summary-card strong {
  font-size: 13.5px;
  line-height: 1.25;
}

.goal-line,
.forecast-legend,
.panel-title,
.risk-row,
.activity-panel dl div,
.company-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.goal-line {
  font-size: 12.5px;
}

.goal-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--surface-muted);
}

.goal-track i,
.funnel-list i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--brand);
}

.analytics-main-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.08fr);
  gap: 12px;
}

.analytics-main-grid.lower {
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
}

.analytics-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
  padding: 16px;
}

.analytics-panel > * {
  min-width: 0;
  width: 100%;
}

.panel-title {
  align-items: flex-start;
}

.panel-title > span {
  width: auto;
  max-width: 48%;
  border-radius: 999px;
  padding: 5px 9px;
  color: var(--brand-strong);
  background: var(--brand-soft);
  font-size: 11.5px;
  font-weight: 700;
  line-height: 1.15;
  overflow-wrap: anywhere;
}

.panel-title h3 {
  font-size: 16px;
  line-height: 1.15;
}

.panel-title .eyebrow {
  margin-bottom: 2px;
  font-size: 10.5px;
}

.chart-frame {
  width: 100%;
  min-width: 0;
}

.forecast-panel svg {
  display: block;
  width: 100%;
  height: 210px;
}

.forecast-legend {
  font-size: 12px;
}

.funnel-list {
  display: grid;
  gap: 10px;
  width: 100%;
}

.funnel-list article {
  display: grid;
  grid-template-columns: minmax(92px, 0.55fr) minmax(160px, 1fr) minmax(102px, 0.5fr);
  gap: 14px;
  align-items: center;
  min-width: 0;
  width: 100%;
  font-size: 12.5px;
}

.funnel-list article > span {
  min-width: 0;
  overflow-wrap: anywhere;
  line-height: 1.18;
}

.funnel-list div {
  width: 100%;
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--surface-muted);
}

.funnel-list small {
  color: var(--muted);
  font-size: 12px;
  text-align: right;
}

.funnel-list .bottleneck span,
.funnel-list .bottleneck small {
  color: var(--warning);
  font-weight: 700;
}

.funnel-list .bottleneck i,
.risk-row i.medium {
  background: var(--warning);
}

.risk-panel,
.activity-panel {
  align-content: start;
}

.risk-row,
.company-row {
  min-height: 42px;
  border-top: 1px solid var(--line-soft);
  padding-top: 10px;
  color: inherit;
  font-size: 12.5px;
  text-decoration: none;
}

.risk-row i {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--success);
}

.risk-row i.high {
  background: var(--danger);
}

.risk-row span,
.company-row div {
  flex: 1;
  min-width: 0;
}

.risk-row span,
.company-row strong,
.company-row small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.risk-row strong {
  flex: 0 0 auto;
  font-size: 13px;
}

.activity-panel dl {
  display: grid;
  gap: 0;
  width: 100%;
  margin: 0;
}

.activity-panel dl div {
  border-top: 1px solid var(--line-soft);
  padding: 11px 0;
  font-size: 12.5px;
}

.activity-panel dd {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
}

.ask-analytics {
  display: grid;
  gap: 6px;
  width: 100%;
  border-radius: 8px;
  padding: 12px;
  background: #f7f8fa;
}

.ask-analytics span {
  font-size: 12.5px;
  font-weight: 800;
}

.ask-analytics small {
  font-size: 12px;
  line-height: 1.25;
}

.company-strip {
  grid-template-columns: minmax(220px, 0.6fr) repeat(3, minmax(0, 1fr));
  align-items: center;
}

.company-strip .panel-title {
  width: auto;
}

.company-row {
  border-top: 0;
  padding-top: 0;
}

.company-row i {
  display: grid;
  flex: 0 0 34px;
  height: 34px;
  place-items: center;
  border-radius: 50%;
  color: #ffffff;
  background: var(--success);
  font-style: normal;
  font-weight: 800;
}

.company-row i.medium {
  background: var(--warning);
}

.company-row i.high {
  background: var(--danger);
}

.next-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 16px 18px;
}

.next-action strong {
  display: block;
  margin-top: 4px;
  font-size: 13.5px;
  line-height: 1.35;
  font-weight: 700;
}

.next-action .button-link {
  flex: 0 0 auto;
  white-space: nowrap;
}

.empty {
  margin: 0;
  padding: 16px;
  color: var(--muted);
  text-align: center;
}

.empty.compact {
  padding: 8px 0 0;
  text-align: left;
}

@media (max-width: 1320px) {
  .analytics-top-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ai-summary-card {
    grid-column: span 2;
  }

  .company-strip {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .analytics-head,
  .next-action {
    align-items: stretch;
    flex-direction: column;
  }

  .analytics-main-grid,
  .analytics-main-grid.lower {
    grid-template-columns: 1fr;
  }

  .analytics-actions,
  .next-action .button-link {
    width: 100%;
  }

  .analytics-actions button {
    flex: 1;
  }

  .funnel-list article {
    grid-template-columns: 1fr;
  }

  .funnel-list small {
    text-align: left;
  }
}

@media (max-width: 560px) {
  .analytics-top-grid {
    grid-template-columns: 1fr;
  }

  .ai-summary-card {
    grid-column: auto;
  }
}
</style>
