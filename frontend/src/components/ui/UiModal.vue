<script setup lang="ts">
import { computed, ref, toRef } from "vue";

import UiButton from "./UiButton.vue";
import { useOverlay } from "./useOverlay";

const props = withDefaults(defineProps<{ open: boolean; title: string; description?: string; size?: "small" | "standard" | "large"; closeOnBackdrop?: boolean }>(), {
  description: undefined,
  size: "standard",
  closeOnBackdrop: true
});
const emit = defineEmits<{ close: [] }>();
const root = ref<HTMLElement | null>(null);
const openRef = toRef(props, "open");
const labelledBy = computed(() => `modal-title-${props.title.toLowerCase().replace(/\W+/g, "-")}`);

function backdropClose() {
  if (props.closeOnBackdrop) emit("close");
}

useOverlay(openRef, root, () => emit("close"));
</script>

<template>
  <Teleport to="body">
    <Transition name="ui-modal">
      <div v-if="open" class="ui-modal-layer" @mousedown.self="backdropClose">
        <section ref="root" class="ui-modal-card" :class="`is-${size}`" role="dialog" aria-modal="true" :aria-labelledby="labelledBy" tabindex="-1">
          <header class="ui-modal__header">
            <div><h2 :id="labelledBy">{{ title }}</h2><p v-if="description">{{ description }}</p></div>
            <UiButton variant="ghost" icon="close" icon-only aria-label="Закрыть" @click="$emit('close')" />
          </header>
          <div class="ui-modal__body"><slot /></div>
          <footer v-if="$slots.footer" class="ui-modal__footer"><slot name="footer" /></footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.ui-modal-layer { position:fixed; inset:0; z-index:130; display:grid; place-items:center; padding:36px 48px; background:var(--color-overlay); backdrop-filter:blur(6px); }
.ui-modal-card { display:flex; flex-direction:column; width:min(560px,calc(100vw - 96px)); max-height:calc(100vh - 72px); overflow:hidden; border:1px solid var(--color-border); border-radius:var(--radius-modal); background:var(--color-surface); box-shadow:var(--shadow-modal); }
.ui-modal-card.is-small { width:min(420px,calc(100vw - 96px)); }
.ui-modal-card.is-large { width:min(960px,calc(100vw - 96px)); }
.ui-modal__header { display:flex; align-items:flex-start; justify-content:space-between; gap:var(--space-4); border-bottom:1px solid var(--color-border-subtle); padding:var(--space-5) var(--space-6); }
.ui-modal__header h2 { margin:0; color:var(--color-text-primary); font-size:20px; line-height:28px; }
.ui-modal__header p { margin:4px 0 0; color:var(--color-text-muted); font-size:13px; line-height:18px; }
.ui-modal__body { min-height:0; overflow-y:auto; padding:var(--space-6); }
.ui-modal__footer { display:flex; justify-content:flex-end; gap:var(--space-2); border-top:1px solid var(--color-border-subtle); padding:var(--space-4) var(--space-6); }
.ui-modal-enter-active,.ui-modal-leave-active { transition:opacity var(--duration-layout) ease; }
.ui-modal-enter-active .ui-modal-card,.ui-modal-leave-active .ui-modal-card { transition:transform var(--duration-layout) ease; }
.ui-modal-enter-from,.ui-modal-leave-to { opacity:0; }
.ui-modal-enter-from .ui-modal-card,.ui-modal-leave-to .ui-modal-card { transform:translateY(8px) scale(.99); }
@media(max-width:640px){.ui-modal-layer{padding:0}.ui-modal-card,.ui-modal-card.is-small,.ui-modal-card.is-large{width:100vw;max-height:100vh;height:100vh;border:0;border-radius:0}.ui-modal__header,.ui-modal__body,.ui-modal__footer{padding-inline:var(--space-4)}}
@media(prefers-reduced-motion:reduce){.ui-modal-enter-active,.ui-modal-leave-active,.ui-modal-enter-active .ui-modal-card,.ui-modal-leave-active .ui-modal-card{transition-duration:.01ms}}
</style>

