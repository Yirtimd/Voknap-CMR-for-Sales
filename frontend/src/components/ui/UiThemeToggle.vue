<script setup lang="ts">
import { useTheme, type ThemePreference } from "../../design-system/theme";
import UiIcon from "./UiIcon.vue";

const { preference, setTheme } = useTheme();
const items: Array<{ value: ThemePreference; label: string; icon: "sun" | "monitor" | "moon" }> = [
  { value: "light", label: "Светлая", icon: "sun" },
  { value: "system", label: "Системная", icon: "monitor" },
  { value: "dark", label: "Тёмная", icon: "moon" }
];
</script>

<template>
  <div class="ui-theme" role="group" aria-label="Тема интерфейса">
    <button
      v-for="item in items"
      :key="item.value"
      type="button"
      :class="{ active: preference === item.value }"
      :aria-label="`${item.label} тема`"
      :title="`${item.label} тема`"
      @click="setTheme(item.value)"
    >
      <UiIcon :name="item.icon" :size="16" /><span>{{ item.label }}</span>
    </button>
  </div>
</template>

<style scoped>
.ui-theme{display:grid;grid-template-columns:repeat(3,1fr);gap:3px;border:1px solid var(--color-border);border-radius:var(--radius-control);padding:3px;background:var(--color-surface-muted)}
.ui-theme button{display:flex;align-items:center;justify-content:center;gap:6px;min-width:0;min-height:32px;border:0;border-radius:var(--radius-sm);padding:0 8px;color:var(--color-text-muted);background:transparent;box-shadow:none;font-size:var(--font-size-meta)}
.ui-theme button:hover{color:var(--color-text-secondary);background:var(--color-surface-subtle)}
.ui-theme button.active{color:var(--color-primary);background:var(--color-surface);box-shadow:var(--shadow-card)}
@media(max-width:1160px){.ui-theme span{display:none}}
</style>
