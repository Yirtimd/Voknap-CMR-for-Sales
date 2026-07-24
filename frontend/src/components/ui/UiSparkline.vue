<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(defineProps<{
  values: number[];
  label: string;
  tone?: "primary" | "success" | "warning" | "danger" | "ai";
  width?: number;
  height?: number;
}>(), {
  tone: "primary",
  width: 240,
  height: 72
});

const points = computed(() => {
  if (!props.values.length) return "";
  const min = Math.min(...props.values);
  const max = Math.max(...props.values);
  const range = Math.max(1, max - min);
  return props.values.map((value, index) => {
    const x = props.values.length === 1 ? props.width / 2 : (index / (props.values.length - 1)) * props.width;
    const y = props.height - 4 - ((value - min) / range) * (props.height - 8);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
});
</script>

<template>
  <figure class="ui-sparkline" :class="`is-${tone}`">
    <svg :viewBox="`0 0 ${width} ${height}`" role="img" :aria-label="label" preserveAspectRatio="none">
      <polyline :points="points" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
    </svg>
    <figcaption>{{ label }}</figcaption>
  </figure>
</template>

<style scoped>
.ui-sparkline{display:grid;gap:6px;margin:0;color:var(--color-primary)}.ui-sparkline svg{width:100%;height:auto;min-height:56px}.ui-sparkline figcaption{color:var(--color-text-muted);font-size:var(--font-size-meta);line-height:var(--line-height-meta)}
.is-success{color:var(--color-success)}.is-warning{color:var(--color-warning)}.is-danger{color:var(--color-danger)}.is-ai{color:var(--color-ai)}
</style>
