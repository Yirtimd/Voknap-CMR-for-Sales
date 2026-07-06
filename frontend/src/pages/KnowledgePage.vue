<script setup lang="ts">
import { onMounted } from "vue";

import { crmStore } from "../stores/crm";

onMounted(() => {
  void crmStore.refreshKnowledge();
});
</script>

<template>
  <section class="section-grid">
    <form class="panel" @submit.prevent="crmStore.createKnowledgeDocument">
      <h2>Новый документ</h2>
      <label>Название<input v-model="crmStore.knowledgeDocumentForm.value.title" /></label>
      <label>Тип источника<input v-model="crmStore.knowledgeDocumentForm.value.source_type" /></label>
      <label>Текст<textarea v-model="crmStore.knowledgeDocumentForm.value.text" class="large-textarea"></textarea></label>
      <button type="submit">Добавить в базу</button>
    </form>

    <section class="panel">
      <h2>Документы</h2>
      <div v-for="document in crmStore.knowledgeDocuments.value" :key="document.id" class="list-row">
        <span>{{ document.title }}</span>
        <small>{{ document.chunks_count }} chunks · {{ document.status }}</small>
      </div>
      <p v-if="!crmStore.knowledgeDocuments.value.length" class="empty">Документов пока нет</p>
    </section>

    <form class="panel" @submit.prevent="crmStore.searchKnowledge">
      <h2>Поиск</h2>
      <label>Запрос<input v-model="crmStore.knowledgeSearchForm.value.query" /></label>
      <label>Лимит<input v-model.number="crmStore.knowledgeSearchForm.value.limit" type="number" min="1" max="20" /></label>
      <button type="submit">Найти</button>
    </form>

    <form class="panel" @submit.prevent="crmStore.askKnowledge">
      <h2>Вопрос к базе</h2>
      <label>Вопрос<input v-model="crmStore.knowledgeAskForm.value.question" /></label>
      <label>Лимит источников<input v-model.number="crmStore.knowledgeAskForm.value.limit" type="number" min="1" max="12" /></label>
      <button type="submit">Спросить</button>
    </form>

    <section class="panel wide">
      <h2>Ответ</h2>
      <p v-if="crmStore.knowledgeAnswer.value" class="answer-text">
        {{ crmStore.knowledgeAnswer.value.answer }}
      </p>
      <p v-else class="empty">Ответа пока нет</p>

      <div
        v-for="citation in crmStore.knowledgeAnswer.value?.citations ?? []"
        :key="citation.chunk_id"
        class="source-card"
      >
        <strong>{{ citation.document_title }}</strong>
        <small>chunk {{ citation.chunk_index }} · score {{ citation.score.toFixed(3) }}</small>
        <p>{{ citation.text }}</p>
      </div>
    </section>

    <section class="panel wide">
      <h2>Результаты поиска</h2>
      <div v-for="result in crmStore.knowledgeSearchResults.value" :key="result.chunk_id" class="source-card">
        <strong>{{ result.document_title }}</strong>
        <small>chunk {{ result.chunk_index }} · score {{ result.score.toFixed(3) }}</small>
        <p>{{ result.text }}</p>
      </div>
      <p v-if="!crmStore.knowledgeSearchResults.value.length" class="empty">Результатов пока нет</p>
    </section>
  </section>
</template>
