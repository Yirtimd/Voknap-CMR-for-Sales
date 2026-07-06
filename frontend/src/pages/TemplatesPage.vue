<script setup lang="ts">
import { computed, onMounted } from "vue";

import { crmStore } from "../stores/crm";

onMounted(() => {
  void crmStore.refreshTemplates();
});

const selectedTemplate = computed(() =>
  crmStore.companyTemplates.value.find(
    (template) => template.code === crmStore.templateApplyForm.value.template_code
  )
);
</script>

<template>
  <section class="section-grid">
    <form class="panel" @submit.prevent="crmStore.applyCompanyTemplate">
      <h2>Применить шаблон</h2>
      <label>Тип компании
        <select v-model="crmStore.templateApplyForm.value.template_code">
          <option v-for="template in crmStore.companyTemplates.value" :key="template.code" :value="template.code">
            {{ template.title }}
          </option>
        </select>
      </label>
      <label class="check-row">
        <input v-model="crmStore.templateApplyForm.value.include_pipeline" type="checkbox" />
        Создать воронку
      </label>
      <label class="check-row">
        <input v-model="crmStore.templateApplyForm.value.include_knowledge" type="checkbox" />
        Добавить playbook в базу знаний
      </label>
      <button type="submit">Применить</button>
    </form>

    <section class="panel">
      <h2>Что будет создано</h2>
      <template v-if="selectedTemplate">
        <p class="hint">{{ selectedTemplate.description }}</p>
        <strong>{{ selectedTemplate.pipeline_name }}</strong>
        <div class="tag-list">
          <span v-for="stage in selectedTemplate.stages" :key="stage" class="tag">{{ stage }}</span>
        </div>
        <p class="hint">{{ selectedTemplate.ai_instruction }}</p>
      </template>
    </section>

    <section class="panel wide">
      <h2>Доступные шаблоны</h2>
      <div v-for="template in crmStore.companyTemplates.value" :key="template.code" class="template-card">
        <header>
          <strong>{{ template.title }}</strong>
          <small>{{ template.code }}</small>
        </header>
        <p>{{ template.description }}</p>
        <div class="tag-list">
          <span v-for="source in template.lead_sources" :key="source" class="tag">{{ source }}</span>
        </div>
      </div>
    </section>

    <section class="panel wide">
      <h2>Примененные шаблоны</h2>
      <div v-for="applied in crmStore.appliedTemplates.value" :key="applied.id" class="entity-row">
        <div>
          <strong>{{ applied.template_title }}</strong>
          <small>{{ applied.template_code }} · {{ applied.status }}</small>
        </div>
        <small>{{ applied.created_at }}</small>
      </div>
      <p v-if="!crmStore.appliedTemplates.value.length" class="empty">Шаблоны еще не применялись</p>
    </section>
  </section>
</template>
