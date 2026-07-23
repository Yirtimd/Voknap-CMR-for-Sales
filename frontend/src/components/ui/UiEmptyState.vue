<script setup lang="ts">
import UiIcon from "./UiIcon.vue";
import type { IconName } from "./icons";

withDefaults(defineProps<{ title: string; description?: string; icon?: IconName; compact?: boolean }>(), {
  description: undefined,
  icon: "file",
  compact: false
});
</script>

<template>
  <section class="ui-empty" :class="{ compact }">
    <span class="ui-empty__icon"><UiIcon :name="icon" :size="22" /></span>
    <strong>{{ title }}</strong>
    <p v-if="description">{{ description }}</p>
    <div v-if="$slots.actions" class="ui-empty__actions"><slot name="actions" /></div>
  </section>
</template>

<style scoped>
.ui-empty { display:grid; justify-items:center; gap:var(--space-2); border:1px dashed var(--color-border-strong); border-radius:var(--radius-card); padding:var(--space-10) var(--space-6); color:var(--color-text-muted); background:var(--color-surface-subtle); text-align:center; }
.ui-empty.compact { padding:var(--space-6); }
.ui-empty__icon { display:grid; place-items:center; width:44px; height:44px; border-radius:var(--radius-pill); color:var(--color-primary); background:var(--color-primary-soft); }
.ui-empty strong { color:var(--color-text-primary); font-size:16px; }
.ui-empty p { max-width:440px; margin:0; font-size:13px; line-height:19px; }
.ui-empty__actions { display:flex; flex-wrap:wrap; justify-content:center; gap:var(--space-2); margin-top:var(--space-2); }
</style>

