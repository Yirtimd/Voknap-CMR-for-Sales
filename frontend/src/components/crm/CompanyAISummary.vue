<script setup lang="ts">
import type { CompanyWorkspace } from "../../types";

defineProps<{ workspace: CompanyWorkspace }>();
</script>

<template>
  <section class="panel">
    <h2>Сводка AI</h2>
    <p class="answer-text">{{ workspace.ai_summary }}</p>
    <div class="risk-list">
      <span v-for="insight in workspace.ai_insights" :key="insight">{{ insight }}</span>
      <span v-if="!workspace.ai_insights.length">Активных рисков не обнаружено.</span>
    </div>
  </section>
</template>
