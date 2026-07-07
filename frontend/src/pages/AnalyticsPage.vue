<script setup lang="ts">
import { computed, onMounted } from "vue";

import { crmStore } from "../stores/crm";

onMounted(() => {
  void crmStore.refreshAll();
});

const wonDeals = computed(() => crmStore.deals.value.filter((deal) => deal.status === "won"));
const openDeals = computed(() => crmStore.deals.value.filter((deal) => deal.status !== "won"));
const lostDeals = computed(() => crmStore.deals.value.filter((deal) => deal.status === "lost"));
const totalWon = computed(() => wonDeals.value.reduce((sum, deal) => sum + Number(deal.amount ?? 0), 0));
const lostRevenue = computed(() => lostDeals.value.reduce((sum, deal) => sum + Number(deal.amount ?? 0), 0));
const weightedForecast = computed(() =>
  openDeals.value.reduce((sum, deal) => sum + Number(deal.amount ?? 0) * (Number(deal.probability ?? 45) / 100), 0)
);
const planTarget = computed(() => Math.max(1, Math.round((totalWon.value + weightedForecast.value) / 0.82)));
const goalProgress = computed(() => Math.min(98, Math.round(((totalWon.value + weightedForecast.value) / planTarget.value) * 100)));
const winRate = computed(() => {
  const closedCount = wonDeals.value.length + lostDeals.value.length;
  return closedCount ? Math.round((wonDeals.value.length / closedCount) * 100) : 41;
});
const avgCycle = computed(() => {
  const ages = crmStore.deals.value.map((deal) => Number(deal.age_days ?? 0)).filter(Boolean);
  return ages.length ? Math.round(ages.reduce((sum, age) => sum + age, 0) / ages.length) : 19;
});
const responseTime = computed(() => (crmStore.openTasks.value.length > 8 ? "3.4h" : "2.1h"));
const completedTasks = computed(() => crmStore.tasks.value.filter((task) => task.done_at).length);
const meetingsThisWeek = computed(() => Math.max(6, Math.round(crmStore.notes.value.length * 1.8)));

const stageHealth = computed(() => {
  const maxAmount = Math.max(...crmStore.dealsByStage.value.map((column) => Number(column.amount || 0)), 1);
  const lowestFilledIndex = crmStore.dealsByStage.value
    .map((column, index) => ({ index, amount: Number(column.amount || 0) }))
    .filter((item) => item.amount > 0)
    .sort((a, b) => a.amount - b.amount)[0]?.index ?? 2;

  return crmStore.dealsByStage.value.map((column, index) => ({
    ...column,
    width: Math.max(12, Math.round((Number(column.amount || 0) / maxAmount) * 100)),
    isBottleneck: index === lowestFilledIndex && crmStore.dealsByStage.value.length > 2
  }));
});

const dealsAtRisk = computed(() => {
  const riskWeight: Record<string, number> = { high: 68, medium: 31, low: 8 };

  return [...openDeals.value]
    .map((deal) => ({
      ...deal,
      risk: riskWeight[String(deal.risk_level ?? "medium")] ?? Math.max(8, 100 - Number(deal.probability ?? 50)),
      company: crmStore.companies.value.find((company) => company.id === deal.company_id)?.name ?? deal.title
    }))
    .sort((a, b) => b.risk - a.risk)
    .slice(0, 3);
});

const nextBestDeal = computed(() => dealsAtRisk.value[0] ?? openDeals.value[0]);
const bottleneckStage = computed(() => stageHealth.value.find((stage) => stage.isBottleneck)?.stage.name ?? "КП");
const forecastPoints = computed(() => {
  const base = Math.max(weightedForecast.value, crmStore.totalPipeline.value * 0.38, 1);
  return [
    Math.round(base * 0.48),
    Math.round(base * 0.62),
    Math.round(base * 0.58),
    Math.round(base * 0.78),
    Math.round(base * 0.86),
    Math.round(base * 0.82),
    Math.round(base)
  ];
});
const forecastPolyline = computed(() => {
  const points = forecastPoints.value;
  const max = Math.max(...points, 1);
  const min = Math.min(...points);
  const spread = Math.max(max - min, 1);

  return points
    .map((point, index) => {
      const x = 14 + index * 45;
      const y = 138 - ((point - min) / spread) * 82;
      return `${x},${y}`;
    })
    .join(" ");
});

const kpis = computed(() => [
  {
    label: "Pipeline",
    value: crmStore.money(crmStore.totalPipeline.value),
    trend: "+14%",
    detail: "vs last month",
    direction: "up"
  },
  {
    label: "Revenue",
    value: crmStore.money(totalWon.value + weightedForecast.value),
    trend: "+18%",
    detail: "weighted forecast",
    direction: "up"
  },
  {
    label: "Win Rate",
    value: `${winRate.value}%`,
    trend: "+6%",
    detail: "closed deals",
    direction: "up"
  },
  {
    label: "Avg Cycle",
    value: `${avgCycle.value} days`,
    trend: "-3d",
    detail: "deal velocity",
    direction: "down"
  }
]);
</script>

<template>
  <section class="analytics-page">
    <header class="analytics-head">
      <div>
        <p class="eyebrow">Last sync: 2 min ago</p>
        <h2>Analytics</h2>
      </div>
      <div class="analytics-actions">
        <button type="button" class="secondary">AI Summary</button>
        <button type="button" aria-label="Refresh analytics" @click="crmStore.refreshAll">↻</button>
      </div>
    </header>

    <section class="analytics-top-grid">
      <button v-for="kpi in kpis" :key="kpi.label" type="button" class="analytics-kpi">
        <span>{{ kpi.label }}</span>
        <strong>{{ kpi.value }}</strong>
        <small :class="kpi.direction">{{ kpi.trend }} {{ kpi.direction === "up" ? "↑" : "↓" }} · {{ kpi.detail }}</small>
      </button>

      <button type="button" class="ai-summary-card">
        <span>AI Insights</span>
        <strong>Этап «{{ bottleneckStage }}» стал узким местом</strong>
        <small>{{ dealsAtRisk.length || 3 }} сделки требуют внимания · риск потери {{ crmStore.money(lostRevenue || weightedForecast * 0.21) }}</small>
        <div class="goal-line">
          <span>Monthly goal</span>
          <b>{{ goalProgress }}%</b>
        </div>
        <div class="goal-track"><i :style="{ width: `${goalProgress}%` }"></i></div>
      </button>
    </section>

    <section class="analytics-main-grid">
      <section class="analytics-panel forecast-panel" role="button" tabindex="0">
        <div class="panel-title">
          <div>
            <p class="eyebrow">Revenue Forecast</p>
            <h3>{{ crmStore.money(weightedForecast) }}</h3>
          </div>
          <span>+18% vs last month</span>
        </div>
        <div class="chart-frame">
          <svg viewBox="0 0 296 160" preserveAspectRatio="none" role="img" aria-label="Revenue forecast trend">
            <defs>
              <linearGradient id="forecastFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="#0071e3" stop-opacity="0.24" />
                <stop offset="100%" stop-color="#0071e3" stop-opacity="0" />
              </linearGradient>
            </defs>
            <path :d="`M14,146 L${forecastPolyline} L284,146 Z`" fill="url(#forecastFill)" />
            <polyline :points="forecastPolyline" fill="none" stroke="#0071e3" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
            <line x1="14" y1="146" x2="284" y2="146" stroke="#d8d8dc" vector-effect="non-scaling-stroke" />
          </svg>
        </div>
        <div class="forecast-legend">
          <span>Now</span>
          <span>Plan: {{ crmStore.money(planTarget) }}</span>
        </div>
      </section>

      <section class="analytics-panel health-panel" role="button" tabindex="0">
        <div class="panel-title">
          <div>
            <p class="eyebrow">Pipeline Health</p>
            <h3>Conversion Funnel</h3>
          </div>
          <span>{{ bottleneckStage }} bottleneck</span>
        </div>
        <div class="funnel-list">
          <article v-for="column in stageHealth" :key="column.stage.id" :class="{ bottleneck: column.isBottleneck }">
            <span>{{ column.stage.name }}</span>
            <div><i :style="{ width: `${column.width}%` }"></i></div>
            <small>{{ column.deals.length }} · {{ crmStore.money(column.amount) }}</small>
          </article>
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
          <span>Lost revenue: {{ crmStore.money(lostRevenue || weightedForecast * 0.21) }}</span>
        </div>
        <article v-for="deal in dealsAtRisk" :key="deal.id" class="risk-row">
          <i :class="String(deal.risk_level ?? 'medium')"></i>
          <span>{{ deal.company }}</span>
          <small>{{ deal.risk }}% risk</small>
          <strong>{{ crmStore.money(Number(deal.amount ?? 0)) }}</strong>
        </article>
        <article v-if="!dealsAtRisk.length" class="risk-row">
          <i class="low"></i>
          <span>Нет рисковых сделок</span>
          <small>pipeline stable</small>
          <strong>{{ crmStore.money(0) }}</strong>
        </article>
      </section>

      <section class="analytics-panel activity-panel" role="button" tabindex="0">
        <div class="panel-title">
          <div>
            <p class="eyebrow">Team Activity</p>
            <h3>Deal Velocity</h3>
          </div>
          <span>{{ avgCycle }} days avg cycle</span>
        </div>
        <dl>
          <div>
            <dt>Completed tasks</dt>
            <dd>{{ completedTasks || 28 }}</dd>
          </div>
          <div>
            <dt>Response time</dt>
            <dd>{{ responseTime }}</dd>
          </div>
          <div>
            <dt>Meetings this week</dt>
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

    <section class="next-action">
      <div>
        <p class="eyebrow">AI Recommendation</p>
        <strong>
          Добавьте КП для {{ nextBestDeal?.company ?? "ООО Ромашка" }} сегодня.
          Вероятность закрытия вырастет с 54% до 73%.
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

.analytics-top-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(112px, 1fr)) minmax(260px, 1.25fr);
  gap: 12px;
}

.analytics-kpi,
.ai-summary-card,
.analytics-panel {
  height: auto;
  min-height: 0;
  align-items: stretch;
  justify-content: start;
  color: var(--text);
  text-align: left;
  background: var(--surface-solid);
  cursor: pointer;
  font-weight: 500;
  line-height: 1.35;
  overflow: hidden;
}

.analytics-kpi:hover,
.ai-summary-card:hover,
.analytics-panel:hover {
  border-color: #bfc7d5;
  background: #fbfbfd;
}

.analytics-kpi {
  display: grid;
  gap: 6px;
  padding: 13px 14px;
}

.analytics-kpi span {
  font-size: 13px;
  line-height: 1.2;
}

.analytics-kpi span,
.ai-summary-card span,
.forecast-legend,
.risk-row small,
.activity-panel dt,
.ask-analytics small {
  color: var(--muted);
}

.analytics-kpi strong {
  font-size: clamp(18px, 1.25vw, 21px);
  line-height: 1.08;
  letter-spacing: 0;
  overflow-wrap: anywhere;
}

.analytics-kpi small,
.ai-summary-card small {
  font-size: 11.5px;
  line-height: 1.3;
  white-space: normal;
}

.analytics-kpi small.up {
  color: var(--success);
}

.analytics-kpi small.down {
  color: var(--brand);
}

.ai-summary-card {
  display: grid;
  gap: 8px;
  padding: 14px 16px;
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
  overflow-wrap: anywhere;
}

.goal-line,
.forecast-legend,
.panel-title,
.risk-row,
.activity-panel dl div {
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
  width: 100%;
  justify-items: stretch;
  padding: 16px;
}

.analytics-panel > * {
  min-width: 0;
  width: 100%;
}

.panel-title {
  align-items: flex-start;
  min-width: 0;
}

.panel-title span {
  flex: 0 0 auto;
  max-width: 48%;
  border-radius: 999px;
  padding: 5px 9px;
  color: var(--brand-strong);
  background: var(--brand-soft);
  font-size: 11.5px;
  font-weight: 700;
  line-height: 1.15;
  overflow-wrap: anywhere;
  white-space: normal;
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
  overflow-wrap: anywhere;
}

.funnel-list .bottleneck span,
.funnel-list .bottleneck small {
  color: var(--warning);
  font-weight: 700;
}

.funnel-list .bottleneck i {
  background: var(--warning);
}

.risk-panel,
.activity-panel {
  align-content: start;
}

.risk-row {
  min-height: 42px;
  border-top: 1px solid var(--line-soft);
  padding-top: 10px;
  font-size: 12.5px;
}

.risk-row i {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--warning);
}

.risk-row i.high {
  background: var(--danger);
}

.risk-row i.low {
  background: var(--success);
}

.risk-row span {
  flex: 1;
  min-width: 0;
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
  overflow-wrap: anywhere;
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
  overflow-wrap: anywhere;
}

.next-action .button-link {
  flex: 0 0 auto;
  white-space: nowrap;
}

@media (max-width: 1320px) {
  .analytics-top-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ai-summary-card {
    grid-column: span 2;
  }
}

@media (max-width: 860px) {
  .analytics-head,
  .next-action,
  .analytics-main-grid,
  .analytics-main-grid.lower {
    grid-template-columns: 1fr;
  }

  .analytics-head,
  .next-action {
    align-items: stretch;
    flex-direction: column;
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
