<script setup lang="ts">
withDefaults(defineProps<{ label?: string; loading?: boolean; striped?: boolean }>(), {
  label: "Таблица данных",
  loading: false,
  striped: false
});
</script>

<template>
  <div class="ui-table-wrap" :aria-busy="loading || undefined">
    <table class="ui-table" :class="{ striped }" :aria-label="label">
      <slot />
    </table>
    <div v-if="loading" class="ui-table__loading" role="status">Загрузка данных…</div>
  </div>
</template>

<style scoped>
.ui-table-wrap { position:relative; max-width:100%; overflow:auto; border:1px solid var(--color-border); border-radius:var(--radius-card); background:var(--color-surface); }
.ui-table { width:100%; border-collapse:collapse; color:var(--color-text-secondary); font-family:var(--font-family-sans); font-size:13px; }
.ui-table :deep(th) { position:sticky; top:0; z-index:1; color:var(--color-text-muted); background:var(--color-surface-subtle); font-size:12px; font-weight:600; text-align:left; }
.ui-table :deep(th),.ui-table :deep(td) { border-bottom:1px solid var(--color-border-subtle); padding:12px 14px; }
.ui-table :deep(tbody tr:hover) { background:var(--color-surface-subtle); }
.ui-table.striped :deep(tbody tr:nth-child(even)) { background:var(--color-surface-subtle); }
.ui-table__loading { position:absolute; inset:0; display:grid; place-items:center; color:var(--color-text-muted); background:var(--color-surface-overlay); font-size:13px; }
</style>
