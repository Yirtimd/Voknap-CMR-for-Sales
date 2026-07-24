<script setup lang="ts">
withDefaults(defineProps<{
  width?: string;
  height?: string;
  shape?: "text" | "rect" | "circle";
  animated?: boolean;
}>(), {
  width: "100%",
  height: "1em",
  shape: "text",
  animated: true
});
</script>

<template>
  <span
    class="ui-skeleton"
    :class="[`is-${shape}`, { 'is-animated': animated }]"
    :style="{ width, height }"
    aria-hidden="true"
  ></span>
</template>

<style scoped>
.ui-skeleton{display:block;max-width:100%;background:var(--color-surface-muted)}
.is-text{border-radius:var(--radius-xs)}.is-rect{border-radius:var(--radius-control)}.is-circle{flex:0 0 auto;border-radius:var(--radius-pill)}
.is-animated{background:linear-gradient(90deg,var(--color-surface-muted) 25%,var(--color-border-subtle) 42%,var(--color-surface-muted) 62%);background-size:220% 100%;animation:ui-skeleton-wave 1.35s ease-in-out infinite}
@keyframes ui-skeleton-wave{to{background-position-x:-220%}}
@media(prefers-reduced-motion:reduce){.is-animated{animation:none}}
</style>
