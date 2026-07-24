<script setup lang="ts">
import UiSkeleton from "./UiSkeleton.vue";

withDefaults(defineProps<{ rows?: number; avatar?: boolean; compact?: boolean }>(), {
  rows: 3,
  avatar: false,
  compact: false
});
</script>

<template>
  <div class="ui-skeleton-group" :class="{ compact }" role="status" aria-label="Загрузка">
    <div v-for="row in rows" :key="row" class="ui-skeleton-row">
      <UiSkeleton v-if="avatar" shape="circle" width="40px" height="40px" />
      <div>
        <UiSkeleton :width="row % 2 ? '46%' : '62%'" height="14px" />
        <UiSkeleton width="82%" height="11px" />
      </div>
    </div>
    <span class="sr-only">Загрузка данных…</span>
  </div>
</template>

<style scoped>
.ui-skeleton-group{display:grid}.ui-skeleton-row{display:grid;grid-template-columns:auto minmax(0,1fr);align-items:center;gap:12px;min-height:72px;border-bottom:1px solid var(--color-border-subtle);padding:10px 16px}.ui-skeleton-row>div{display:grid;gap:8px}.compact .ui-skeleton-row,:global(.density-compact) .ui-skeleton-row{min-height:52px;padding-block:7px}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}
</style>
