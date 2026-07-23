<script setup lang="ts">
export type TabItem = { value: string; label: string; count?: number; disabled?: boolean };

withDefaults(defineProps<{ items: TabItem[]; label?: string }>(), { label: "Разделы" });
const model = defineModel<string>({ required: true });
</script>

<template>
  <div class="ui-tabs" role="tablist" :aria-label="label">
    <button
      v-for="item in items"
      :key="item.value"
      type="button"
      role="tab"
      :aria-selected="model === item.value"
      :disabled="item.disabled"
      :class="{ active: model === item.value }"
      @click="model = item.value"
    >
      <span>{{ item.label }}</span>
      <b v-if="item.count !== undefined">{{ item.count }}</b>
    </button>
  </div>
</template>

<style scoped>
.ui-tabs { display:flex; gap:var(--space-5); overflow-x:auto; border-bottom:1px solid var(--color-border); scrollbar-width:none; }
.ui-tabs button { position:relative; display:inline-flex; align-items:center; gap:var(--space-2); min-height:42px; border:0; border-radius:0; padding:0; color:var(--color-text-muted); background:transparent; font-family:var(--font-family-sans); font-size:13px; font-weight:600; white-space:nowrap; cursor:pointer; }
.ui-tabs button:hover { color:var(--color-text-primary); }
.ui-tabs button::after { content:""; position:absolute; right:0; bottom:-1px; left:0; height:2px; background:transparent; }
.ui-tabs button.active { color:var(--color-primary); }
.ui-tabs button.active::after { background:var(--color-primary); }
.ui-tabs button:focus-visible { outline:3px solid var(--color-focus); outline-offset:2px; }
.ui-tabs button:disabled { color:var(--color-text-disabled); cursor:not-allowed; }
.ui-tabs b { display:grid; place-items:center; min-width:20px; height:20px; border-radius:var(--radius-pill); padding:0 6px; color:var(--color-primary-active); background:var(--color-primary-soft); font-size:11px; }
</style>

