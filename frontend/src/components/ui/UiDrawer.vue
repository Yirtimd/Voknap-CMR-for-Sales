<script setup lang="ts">
import { computed, ref, toRef } from "vue";

import UiButton from "./UiButton.vue";
import { useOverlay } from "./useOverlay";

const props = withDefaults(defineProps<{ open: boolean; title: string; description?: string; width?: "standard" | "wide" }>(), {
  description: undefined,
  width: "standard"
});
const emit = defineEmits<{ close: [] }>();
const root = ref<HTMLElement | null>(null);
const openRef = toRef(props, "open");
const labelledBy = computed(() => `drawer-title-${props.title.toLowerCase().replace(/\W+/g, "-")}`);

useOverlay(openRef, root, () => emit("close"));
</script>

<template>
  <Teleport to="body">
    <Transition name="ui-overlay">
      <div v-if="open" class="ui-drawer-layer" @mousedown.self="$emit('close')">
        <aside ref="root" class="ui-drawer" :class="`is-${width}`" role="dialog" aria-modal="true" :aria-labelledby="labelledBy" tabindex="-1">
          <header class="ui-drawer__header">
            <div><h2 :id="labelledBy">{{ title }}</h2><p v-if="description">{{ description }}</p></div>
            <UiButton variant="ghost" icon="close" icon-only aria-label="Закрыть" @click="$emit('close')" />
          </header>
          <div class="ui-drawer__body"><slot /></div>
          <footer v-if="$slots.footer" class="ui-drawer__footer"><slot name="footer" /></footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.ui-drawer-layer { position:fixed; inset:0; z-index:120; display:flex; justify-content:flex-end; background:var(--color-overlay); backdrop-filter:blur(2px); }
.ui-drawer { display:flex; flex-direction:column; width:min(430px,100vw); height:100dvh; border-left:1px solid var(--color-border); background:var(--color-surface); box-shadow:var(--shadow-drawer); }
.ui-drawer.is-wide { width:min(680px,100vw); }
.ui-drawer__header { display:flex; align-items:flex-start; justify-content:space-between; gap:var(--space-4); border-bottom:1px solid var(--color-border-subtle); padding:var(--space-5) var(--space-6); }
.ui-drawer__header h2 { margin:0; color:var(--color-text-primary); font-size:20px; line-height:28px; }
.ui-drawer__header p { margin:4px 0 0; color:var(--color-text-muted); font-size:13px; line-height:18px; }
.ui-drawer__body { flex:1; min-height:0; overflow-y:auto; padding:var(--space-6); }
.ui-drawer__footer { display:flex; justify-content:flex-end; gap:var(--space-2); border-top:1px solid var(--color-border-subtle); padding:var(--space-4) var(--space-6) calc(var(--space-4) + env(safe-area-inset-bottom)); }
.ui-overlay-enter-active,.ui-overlay-leave-active { transition:opacity var(--duration-layout) ease; }
.ui-overlay-enter-active .ui-drawer,.ui-overlay-leave-active .ui-drawer { transition:transform var(--duration-layout) ease; }
.ui-overlay-enter-from,.ui-overlay-leave-to { opacity:0; }
.ui-overlay-enter-from .ui-drawer,.ui-overlay-leave-to .ui-drawer { transform:translateX(24px); }
@media(max-width:640px){.ui-drawer,.ui-drawer.is-wide{width:100dvw;border-left:0}.ui-drawer__header,.ui-drawer__body,.ui-drawer__footer{padding-inline:var(--space-4)}.ui-drawer__header{padding-top:calc(var(--space-4) + env(safe-area-inset-top))}.ui-drawer__footer{position:sticky;bottom:0;flex-wrap:wrap;background:var(--color-surface)}}
@media(prefers-reduced-motion:reduce){.ui-overlay-enter-active,.ui-overlay-leave-active,.ui-overlay-enter-active .ui-drawer,.ui-overlay-leave-active .ui-drawer{transition-duration:.01ms}}
</style>
