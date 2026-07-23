<script setup lang="ts">
withDefaults(defineProps<{ padding?: "none" | "compact" | "standard" | "large"; interactive?: boolean }>(), {
  padding: "standard",
  interactive: false
});
</script>

<template>
  <section class="ui-card" :class="[`has-${padding}-padding`, { 'is-interactive': interactive }]">
    <header v-if="$slots.header || $slots.actions" class="ui-card__header">
      <div><slot name="header" /></div>
      <div v-if="$slots.actions" class="ui-card__actions"><slot name="actions" /></div>
    </header>
    <slot />
    <footer v-if="$slots.footer" class="ui-card__footer"><slot name="footer" /></footer>
  </section>
</template>

<style scoped>
.ui-card { min-width:0; border:1px solid var(--color-border); border-radius:var(--radius-card); background:var(--color-surface); box-shadow:var(--shadow-card); }
.has-none-padding { padding:0; }
.has-compact-padding { padding:var(--space-3); }
.has-standard-padding { padding:var(--space-4); }
.has-large-padding { padding:var(--space-6); }
.is-interactive { transition:border-color var(--duration-standard) ease, box-shadow var(--duration-standard) ease, transform var(--duration-standard) ease; }
.is-interactive:hover { border-color:var(--color-border-strong); box-shadow:var(--shadow-card-hover); transform:translateY(-1px); }
.ui-card__header,.ui-card__footer { display:flex; align-items:center; justify-content:space-between; gap:var(--space-3); }
.ui-card__header { margin-bottom:var(--space-4); }
.ui-card__footer { margin-top:var(--space-4); }
.ui-card__actions { display:flex; align-items:center; gap:var(--space-2); }
</style>
