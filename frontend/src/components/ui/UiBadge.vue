<script setup lang="ts">
import type { StatusTone } from "../../design-system/statusDictionary";

withDefaults(defineProps<{ tone?: StatusTone; size?: "small" | "standard" }>(), {
  tone: "neutral",
  size: "standard"
});
</script>

<template>
  <span class="ui-badge" :class="[`is-${tone}`, `is-${size}`]"><slot /></span>
</template>

<style scoped>
.ui-badge { display:inline-flex; align-items:center; max-width:100%; min-height:24px; border-radius:var(--radius-pill); padding:0 9px; overflow:hidden; color:var(--color-text-secondary); background:var(--color-surface-muted); font-size:12px; line-height:1; font-weight:600; white-space:nowrap; text-overflow:ellipsis; }
.is-small { min-height:20px; padding-inline:7px; font-size:11px; }
.is-info { color:var(--color-primary-active); background:var(--color-primary-soft); }
.is-success { color:var(--color-success-text); background:var(--color-success-soft); }
.is-warning { color:var(--color-warning-text); background:var(--color-warning-soft); }
.is-danger { color:var(--color-danger-text); background:var(--color-danger-soft); }
.is-ai { color:var(--color-ai-hover); background:var(--color-ai-soft); }
</style>

