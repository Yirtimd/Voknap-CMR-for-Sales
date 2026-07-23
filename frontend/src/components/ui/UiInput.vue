<script setup lang="ts">
import { computed, useId, useAttrs } from "vue";

defineOptions({ inheritAttrs: false });

const props = withDefaults(defineProps<{ label?: string; hint?: string; error?: string; id?: string; type?: string }>(), {
  label: undefined,
  hint: undefined,
  error: undefined,
  id: undefined,
  type: "text"
});
const model = defineModel<string | number | null>();
const attrs = useAttrs();
const generatedId = useId();
const controlId = computed(() => props.id ?? generatedId);
const describedBy = computed(() => {
  if (props.error) return `${controlId.value}-error`;
  if (props.hint) return `${controlId.value}-hint`;
  return undefined;
});
</script>

<template>
  <label class="ui-field" :for="controlId">
    <span v-if="label" class="ui-field__label">{{ label }}</span>
    <input
      :id="controlId"
      v-model="model"
      class="ui-input"
      :class="{ 'has-error': error }"
      :type="type"
      :aria-invalid="error ? true : undefined"
      :aria-describedby="describedBy"
      v-bind="attrs"
    />
    <span v-if="error" :id="`${controlId}-error`" class="ui-field__error">{{ error }}</span>
    <span v-else-if="hint" :id="`${controlId}-hint`" class="ui-field__hint">{{ hint }}</span>
  </label>
</template>

<style scoped>
.ui-field { display:grid; gap:6px; margin:0; color:var(--color-text-secondary); font-family:var(--font-family-sans); font-size:13px; font-weight:600; }
.ui-input { width:100%; min-height:var(--control-height); border:1px solid var(--color-border-strong); border-radius:var(--radius-control); padding:0 var(--space-3); outline:0; color:var(--color-text-primary); background:var(--color-surface); font:inherit; font-weight:400; transition:border-color var(--duration-standard) ease, box-shadow var(--duration-standard) ease; }
.ui-input::placeholder { color:var(--color-text-disabled); }
.ui-input:hover { border-color:var(--color-text-disabled); }
.ui-input:focus { border-color:var(--color-primary); box-shadow:0 0 0 3px var(--color-focus); }
.ui-input:disabled { color:var(--color-text-disabled); background:var(--color-surface-muted); cursor:not-allowed; }
.ui-input.has-error { border-color:var(--color-danger); }
.ui-field__hint,.ui-field__error { font-size:12px; line-height:17px; font-weight:400; }
.ui-field__hint { color:var(--color-text-muted); }
.ui-field__error { color:var(--color-danger-text); }
</style>

