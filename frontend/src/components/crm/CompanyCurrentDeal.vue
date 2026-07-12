<script setup lang="ts">
import { computed } from "vue";
import type { CompanyWorkspace } from "../../types";
import { crmStore } from "../../stores/crm";

const props = defineProps<{ workspace: CompanyWorkspace }>();

const currentDeal = computed(() => props.workspace.deals[0]);
const stages = computed(() => crmStore.allStages.value);
const currentStage = computed(() => stages.value.find((stage) => stage.id === currentDeal.value?.stage_id));
const currentStageIndex = computed(() => Math.max(0, stages.value.findIndex((stage) => stage.id === currentDeal.value?.stage_id)));
const progress = computed(() => {
  if (!stages.value.length) return 0;
  return Math.round(((currentStageIndex.value + 1) / stages.value.length) * 100);
});
</script>

<template>
  <section class="panel current-deal-panel">
    <div class="panel-head">
      <div>
        <p class="eyebrow">Current Deal</p>
        <h2>Активная сделка</h2>
      </div>
      <RouterLink class="secondary-link" to="/deals">Open Deals</RouterLink>
    </div>
    <template v-if="currentDeal">
      <div class="deal-focus">
        <div>
          <span>Revenue</span>
          <strong>{{ crmStore.money(currentDeal.amount) }}</strong>
        </div>
        <div>
          <span>Stage</span>
          <strong>{{ currentStage?.name ?? "КП" }}</strong>
        </div>
        <div>
          <span>Probability</span>
          <strong>{{ Math.min(90, 40 + Number(currentDeal.amount ?? 0) / 5000).toFixed(0) }}%</strong>
        </div>
      </div>
      <h3>{{ currentDeal.title }}</h3>
      <div class="stage-path">
        <span
          v-for="stage in stages"
          :key="stage.id"
          :class="{ active: stage.id === currentDeal.stage_id }"
        >{{ stage.name }}</span>
      </div>
      <div class="deal-progress" aria-label="Deal progress">
        <span :style="{ width: `${progress}%` }"></span>
      </div>
      <section class="next-step-card">
        <span>Next Action</span>
        <strong>{{ workspace.next_action?.title ?? currentDeal.next_step ?? "Не назначено" }}</strong>
      </section>
    </template>
    <p v-else class="empty">No active deal. Create first opportunity for this company.</p>
  </section>
</template>
