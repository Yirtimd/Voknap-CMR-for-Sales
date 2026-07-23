<script setup lang="ts">
import { computed, useAttrs, useId } from "vue";

defineOptions({ inheritAttrs: false });

export type SelectOption = { value: string | number; label: string; disabled?: boolean };

const props = withDefaults(defineProps<{ options?: SelectOption[]; label?: string; hint?: string; error?: string; id?: string; placeholder?: string }>(), {
  options: () => [],
  label: undefined,
  hint: undefined,
  error: undefined,
  id: undefined,
  placeholder: undefined
});
const model = defineModel<string | number | null>();
const attrs = useAttrs();
const generatedId = useId();
const controlId = computed(() => props.id ?? generatedId);
</script>

<template>
  <label class="ui-field" :for="controlId">
    <span v-if="label" class="ui-field__label">{{ label }}</span>
    <select
      :id="controlId"
      v-model="model"
      class="ui-select"
      :class="{ 'has-error': error }"
      :aria-invalid="error ? true : undefined"
      v-bind="attrs"
    >
      <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
      <option v-for="option in options" :key="option.value" :value="option.value" :disabled="option.disabled">{{ option.label }}</option>
      <slot />
    </select>
    <span v-if="error" class="ui-field__error">{{ error }}</span>
    <span v-else-if="hint" class="ui-field__hint">{{ hint }}</span>
  </label>
</template>

<style scoped>
.ui-field { display:grid; gap:6px; margin:0; color:var(--color-text-secondary); font-family:var(--font-family-sans); font-size:13px; font-weight:600; }
.ui-select { width:100%; min-height:var(--control-height); border:1px solid var(--color-border-strong); border-radius:var(--radius-control); padding:0 34px 0 var(--space-3); outline:0; color:var(--color-text-primary); background:var(--color-surface); font:inherit; font-weight:400; transition:border-color var(--duration-standard) ease, box-shadow var(--duration-standard) ease; }
.ui-select:hover { border-color:var(--color-text-disabled); }
.ui-select:focus { border-color:var(--color-primary); box-shadow:0 0 0 3px var(--color-focus); }
.ui-select:disabled { color:var(--color-text-disabled); background:var(--color-surface-muted); cursor:not-allowed; }
.ui-select.has-error { border-color:var(--color-danger); }
.ui-field__hint,.ui-field__error { font-size:12px; line-height:17px; font-weight:400; }
.ui-field__hint { color:var(--color-text-muted); }
.ui-field__error { color:var(--color-danger-text); }
</style>
