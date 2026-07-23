<script setup lang="ts">
import UiIcon from "./UiIcon.vue";

withDefaults(defineProps<{ tone?: "info" | "success" | "warning" | "danger"; title?: string; dismissible?: boolean }>(), {
  tone: "info",
  title: undefined,
  dismissible: false
});
defineEmits<{ dismiss: [] }>();
</script>

<template>
  <section class="ui-alert" :class="`is-${tone}`" :role="tone === 'danger' ? 'alert' : 'status'">
    <UiIcon :name="tone === 'success' ? 'check' : tone === 'danger' || tone === 'warning' ? 'alert' : 'sparkles'" :size="20" />
    <div><strong v-if="title">{{ title }}</strong><slot /></div>
    <button v-if="dismissible" type="button" aria-label="Закрыть сообщение" @click="$emit('dismiss')"><UiIcon name="close" :size="18" /></button>
  </section>
</template>

<style scoped>
.ui-alert { display:grid; grid-template-columns:auto minmax(0,1fr) auto; gap:var(--space-3); align-items:start; border:1px solid var(--color-border); border-radius:var(--radius-control); padding:var(--space-3) var(--space-4); color:var(--color-text-secondary); background:var(--color-primary-soft); font-size:13px; line-height:18px; }
.ui-alert strong { display:block; margin-bottom:2px; color:var(--color-text-primary); }
.is-success { color:var(--color-success-text); border-color:var(--color-success); background:var(--color-success-soft); }
.is-warning { color:var(--color-warning-text); border-color:var(--color-warning); background:var(--color-warning-soft); }
.is-danger { color:var(--color-danger-text); border-color:var(--color-danger); background:var(--color-danger-soft); }
.ui-alert button { display:grid; place-items:center; width:28px; height:28px; min-height:0; border:0; padding:0; color:inherit; background:transparent; cursor:pointer; }
</style>

