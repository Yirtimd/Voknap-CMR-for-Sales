<script setup lang="ts">
import { computed } from "vue";

import type { Deal } from "../../types";
import { crmStore } from "../../stores/crm";

const props = defineProps<{ deal: Deal | null }>();
defineEmits<{ close: [] }>();

const activeDeal = computed(() => props.deal);
const companyPath = computed(() => props.deal ? `/companies/${props.deal.company_id}` : "/companies");
const companyName = computed(() =>
  props.deal
    ? crmStore.companies.value.find((item) => item.id === props.deal?.company_id)?.name ?? "Unknown"
    : "Unknown"
);
const stageName = computed(() =>
  props.deal
    ? crmStore.allStages.value.find((item) => item.id === props.deal?.stage_id)?.name ?? "Unknown"
    : "Unknown"
);

function addNote() {
  if (!props.deal) return;
  void crmStore.createNote("deal", props.deal.id);
}
</script>

<template>
  <aside v-if="activeDeal" class="drawer">
    <header>
      <div>
        <p class="eyebrow">Deal Drawer</p>
        <h2>{{ activeDeal.title }}</h2>
      </div>
      <button class="secondary" type="button" @click="$emit('close')">Close</button>
    </header>
    <dl class="drawer-facts">
      <div><dt>Amount</dt><dd>{{ crmStore.money(activeDeal.amount) }}</dd></div>
      <div><dt>Probability</dt><dd>{{ Math.min(90, 40 + Number(activeDeal.amount ?? 0) / 5000).toFixed(0) }}%</dd></div>
      <div><dt>Company</dt><dd>{{ companyName }}</dd></div>
      <div><dt>Stage</dt><dd>{{ stageName }}</dd></div>
    </dl>
    <section>
      <h3>AI Summary</h3>
      <p>Deal needs regular follow-up. Check timeline and confirm next step with buyer.</p>
    </section>
    <section>
      <h3>Timeline</h3>
      <p class="hint">Company timeline is available inside Company Card.</p>
    </section>
    <div class="button-row">
      <button type="button" @click="addNote">Add note</button>
      <RouterLink class="button-link" :to="companyPath">Open company</RouterLink>
    </div>
  </aside>
</template>
