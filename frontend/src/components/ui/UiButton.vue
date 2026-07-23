<script setup lang="ts">
import UiIcon from "./UiIcon.vue";
import type { IconName } from "./icons";

withDefaults(
  defineProps<{
    variant?: "primary" | "secondary" | "ghost" | "danger" | "ai";
    size?: "compact" | "standard" | "prominent";
    type?: "button" | "submit" | "reset";
    icon?: IconName;
    iconPosition?: "start" | "end";
    iconOnly?: boolean;
    loading?: boolean;
    disabled?: boolean;
  }>(),
  {
    variant: "primary",
    size: "standard",
    type: "button",
    icon: undefined,
    iconPosition: "start",
    iconOnly: false,
    loading: false,
    disabled: false
  }
);
</script>

<template>
  <button
    class="ui-button"
    :class="[`is-${variant}`, `is-${size}`, { 'is-icon-only': iconOnly, 'is-loading': loading }]"
    :type="type"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
  >
    <span v-if="loading" class="ui-button__spinner" aria-hidden="true"></span>
    <UiIcon v-else-if="icon && iconPosition === 'start'" :name="icon" :size="18" />
    <span v-if="!iconOnly" class="ui-button__label"><slot /></span>
    <UiIcon v-if="!loading && icon && iconPosition === 'end'" :name="icon" :size="18" />
  </button>
</template>

<style scoped>
.ui-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-width: 0;
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  padding: 0 var(--space-4);
  font-family: var(--font-family-sans);
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition:
    border-color var(--duration-standard) ease,
    background-color var(--duration-standard) ease,
    color var(--duration-standard) ease,
    box-shadow var(--duration-standard) ease;
}
.is-compact { min-height: var(--control-height-compact); padding-inline: var(--space-3); }
.is-standard { min-height: var(--control-height); }
.is-prominent { min-height: var(--control-height-prominent); }
.is-primary { color: var(--color-surface); background: var(--color-primary); }
.is-primary:hover { background: var(--color-primary-hover); }
.is-primary:active { background: var(--color-primary-active); }
.is-secondary { color: var(--color-text-secondary); border-color: var(--color-border-strong); background: var(--color-surface); }
.is-secondary:hover,
.is-ghost:hover { background: var(--color-surface-muted); }
.is-ghost { color: var(--color-text-secondary); background: transparent; }
.is-danger { color: var(--color-surface); background: var(--color-danger); }
.is-danger:hover { background: var(--color-danger-text); }
.is-ai { color: var(--color-surface); background: var(--color-ai); }
.is-ai:hover { background: var(--color-ai-hover); }
.is-icon-only { width: var(--control-height); padding: 0; }
.ui-button:focus-visible { outline: 3px solid var(--color-focus); outline-offset: 2px; }
.ui-button:disabled { color: var(--color-text-disabled); border-color: var(--color-border); background: var(--color-surface-muted); cursor: not-allowed; }
.ui-button__spinner { width: 16px; height: 16px; border: 2px solid currentColor; border-right-color: transparent; border-radius: var(--radius-pill); animation: ui-spin 700ms linear infinite; }
@keyframes ui-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .ui-button__spinner { animation-duration: 1.5s; } }
</style>

