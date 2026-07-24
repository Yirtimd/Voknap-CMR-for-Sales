<script setup lang="ts">
import { useDensity } from "../../design-system/density";
import UiIcon from "./UiIcon.vue";

const { density, setDensity } = useDensity();
</script>

<template>
  <div class="ui-density" role="group" aria-label="Плотность интерфейса">
    <button type="button" :class="{ active: density === 'comfortable' }" aria-label="Комфортная плотность" title="Комфортная плотность" @click="setDensity('comfortable')">
      <UiIcon name="list" :size="16" /><span>Комфортно</span>
    </button>
    <button type="button" :class="{ active: density === 'compact' }" aria-label="Компактная плотность" title="Компактная плотность" @click="setDensity('compact')">
      <UiIcon name="grid" :size="16" /><span>Компактно</span>
    </button>
  </div>
</template>

<style scoped>
.ui-density{display:grid;grid-template-columns:1fr 1fr;gap:3px;border:1px solid var(--color-border);border-radius:var(--radius-control);padding:3px;background:var(--color-surface-muted)}
.ui-density button{display:flex;align-items:center;justify-content:center;gap:6px;min-height:32px;border:0;border-radius:var(--radius-sm);padding:0 9px;color:var(--color-text-muted);background:transparent;box-shadow:none;font-size:var(--font-size-meta)}
.ui-density button.active{color:var(--color-primary);background:var(--color-surface);box-shadow:var(--shadow-card)}
@media(max-width:1100px){.ui-density span{display:none}}
</style>
