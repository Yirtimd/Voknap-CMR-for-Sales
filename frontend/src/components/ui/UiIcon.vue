<script setup lang="ts">
import { iconPaths, type IconName } from "./icons";

withDefaults(defineProps<{ name: IconName; size?: number; strokeWidth?: number; label?: string }>(), {
  size: 20,
  strokeWidth: 1.8,
  label: undefined
});
</script>

<template>
  <svg
    class="ui-icon-svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    :width="size"
    :height="size"
    :aria-hidden="label ? undefined : true"
    :aria-label="label"
    :role="label ? 'img' : undefined"
  >
    <path v-for="path in iconPaths[name]" :key="path" :d="path" />
  </svg>
</template>

<style scoped>
.ui-icon-svg {
  display: block;
  flex: 0 0 auto;
}
</style>

