<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import UiBadge from "../components/ui/UiBadge.vue";
import UiEmptyState from "../components/ui/UiEmptyState.vue";
import UiTabs from "../components/ui/UiTabs.vue";
import { statusMeta } from "../design-system/statusDictionary";
import { crmStore } from "../stores/crm";

const activeTab = ref<"chat" | "documents" | "collections" | "agents" | "settings">("chat");
const brainTabs = [
  { value: "chat", label: "Вопросы" },
  { value: "documents", label: "Документы" },
  { value: "collections", label: "Коллекции" },
  { value: "agents", label: "AI-агенты" },
  { value: "settings", label: "Настройки" }
];
const uploadInput = ref<HTMLInputElement | null>(null);
const uploadFile = ref<File | null>(null);
const uploadTitle = ref("");
const uploadInProgress = ref(false);

const suggestedQuestions = [
  "Как мы квалифицируем лиды?",
  "Где хранятся цены?",
  "Объясни процесс адаптации.",
  "Как мы работаем с крупными клиентами?",
  "Покажи правила компании.",
  "Найди шаблон договора."
];

const relatedKnowledge = [
  { title: "Квалификация лидов", children: ["Сценарий продаж", "Цены", "Исследование", "Предложение"] },
  { title: "Продажи крупным клиентам", children: ["Проверка безопасности", "Участники", "Коммерческие условия"] }
];

const aiActions = ["Создать задачу", "Создать чек-лист", "Открыть документ", "Сделать выжимку", "Объяснить проще", "Создать инструкцию", "Отправить агенту"];

const confidence = computed(() => {
  const citations = crmStore.knowledgeAnswer.value?.citations ?? [];
  if (!citations.length) return 0;
  return Math.min(99, Math.max(72, Math.round(citations[0].score * 100)));
});

const sourceSummary = computed(() => {
  const count = new Set((crmStore.knowledgeAnswer.value?.citations ?? []).map((item) => item.document_id)).size;
  if (!count) return "Задайте вопрос, чтобы увидеть источники ответа.";
  return `Ответ сформирован по документам рабочего пространства: ${count}.`;
});

function askSuggested(question: string) {
  crmStore.knowledgeAskForm.value.question = question;
  void crmStore.askKnowledge();
}

function relevance(score: number) {
  return `Релевантность ${Math.min(99, Math.max(61, Math.round(score * 100)))}%`;
}

function selectUpload(event: Event) {
  uploadFile.value = (event.target as HTMLInputElement).files?.[0] ?? null;
}

async function uploadKnowledgeFile() {
  if (!uploadFile.value) return;
  uploadInProgress.value = true;
  try {
    const succeeded = await crmStore.uploadKnowledgeDocument(uploadFile.value, {
      title: uploadTitle.value,
      scope: "global"
    });
    if (succeeded) {
      uploadFile.value = null;
      uploadTitle.value = "";
      if (uploadInput.value) uploadInput.value.value = "";
    }
  } finally {
    uploadInProgress.value = false;
  }
}

onMounted(() => {
  void crmStore.refreshKnowledge();
});
</script>

<template>
  <section class="brain-page">
    <UiTabs v-model="activeTab" class="brain-tabs" :items="brainTabs" label="Разделы базы знаний" />

    <section v-if="activeTab === 'chat'" class="brain-chat-layout">
      <div class="brain-main">
        <section class="brain-ask">
          <p class="eyebrow">База знаний</p>
          <h2>Добрый день, Дмитрий.</h2>
          <p>Что вы хотите узнать?</p>

          <form class="brain-question" @submit.prevent="crmStore.askKnowledge()">
            <textarea
              v-model="crmStore.knowledgeAskForm.value.question"
              rows="3"
              placeholder="Спросите о продажах, правилах, ценах или договорах..."
            ></textarea>
            <button type="submit">Спросить</button>
          </form>

          <div class="suggested-grid" aria-label="Предлагаемые вопросы">
            <button v-for="question in suggestedQuestions" :key="question" type="button" @click="askSuggested(question)">
              {{ question }}
            </button>
          </div>
        </section>

        <section v-if="crmStore.knowledgeAnswer.value" class="panel brain-answer">
          <div class="brain-answer-head">
            <div>
              <p class="eyebrow">Ответ</p>
              <h2>Ответ по базе знаний</h2>
            </div>
            <div class="confidence-meter">
              <span>Уверенность</span>
              <strong>{{ confidence }}%</strong>
            </div>
          </div>

          <p class="answer-text">{{ crmStore.knowledgeAnswer.value.answer }}</p>

          <div class="reasoning-block">
            <span>Основание ответа</span>
            <p>{{ sourceSummary }}</p>
          </div>

          <div class="ai-actions">
            <button v-for="action in aiActions" :key="action" type="button" class="secondary">{{ action }}</button>
          </div>

          <div class="source-list">
            <h3>Источники</h3>
            <article
              v-for="citation in crmStore.knowledgeAnswer.value.citations"
              :key="citation.chunk_id"
              class="brain-source"
            >
              <div>
                <strong>{{ citation.document_title }}</strong>
                <small>{{ relevance(citation.score) }}</small>
              </div>
              <p>{{ citation.text }}</p>
              <button type="button" class="secondary">Открыть</button>
            </article>
          </div>
        </section>
      </div>

      <aside class="brain-rail">
        <section class="panel compact-panel">
          <h2>Связанные знания</h2>
          <div v-for="group in relatedKnowledge" :key="group.title" class="knowledge-branch">
            <strong>{{ group.title }}</strong>
            <span v-for="child in group.children" :key="child">{{ child }}</span>
          </div>
        </section>

        <section class="panel compact-panel">
          <h2>Документы</h2>
          <div v-for="document in crmStore.knowledgeDocuments.value.slice(0, 4)" :key="document.id" class="document-mini-row">
            <div>
              <strong>{{ document.title }}</strong>
              <small>Фрагментов: {{ document.chunks_count }}</small>
            </div>
            <UiBadge :tone="statusMeta(document.status, 'document').tone">{{ statusMeta(document.status, "document").label }}</UiBadge>
          </div>
          <p v-if="!crmStore.knowledgeDocuments.value.length" class="empty">Документы пока не подключены.</p>
        </section>
      </aside>
    </section>

    <section v-else-if="activeTab === 'documents'" class="documents-workspace">
      <section class="panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Память рабочего пространства</p>
            <h2>Документы</h2>
          </div>
          <button type="button" @click="uploadInput?.click()">Загрузить файл</button>
        </div>

        <form class="document-upload-form" @submit.prevent="uploadKnowledgeFile">
          <label class="wide-field">
            PDF, DOCX or TXT
            <input ref="uploadInput" type="file" accept=".pdf,.docx,.txt" required @change="selectUpload" />
          </label>
          <label>Название, необязательно<input v-model="uploadTitle" placeholder="По умолчанию — имя файла" /></label>
          <button type="submit" :disabled="!uploadFile || uploadInProgress">
            {{ uploadInProgress ? "Обработка и индексация…" : "Загрузить и проиндексировать" }}
          </button>
        </form>

        <form class="document-upload-form" @submit.prevent="crmStore.createKnowledgeDocument">
          <h3 class="wide-field">Или добавьте текст</h3>
          <label>Название<input v-model="crmStore.knowledgeDocumentForm.value.title" required /></label>
          <label>Коллекция<input v-model="crmStore.knowledgeDocumentForm.value.source_type" /></label>
          <label class="wide-field">Содержание<textarea v-model="crmStore.knowledgeDocumentForm.value.text" class="large-textarea" required></textarea></label>
          <button type="submit">Добавить документ</button>
        </form>
      </section>

      <section class="panel">
        <article v-for="document in crmStore.knowledgeDocuments.value" :key="document.id" class="document-row">
          <div>
            <strong>{{ document.title }}</strong>
            <small>Фрагментов: {{ document.chunks_count }} · обновлено {{ new Date(document.created_at).toLocaleDateString("ru-RU") }}</small>
          </div>
          <div>
            <button v-if="document.download_url" type="button" class="secondary" @click="crmStore.downloadKnowledgeDocument(document)">Скачать</button>
            <UiBadge :tone="statusMeta(document.status, 'document').tone">{{ statusMeta(document.status, "document").label }}</UiBadge>
          </div>
        </article>
        <UiEmptyState v-if="!crmStore.knowledgeDocuments.value.length" title="Документов пока нет" description="Загрузите файл или добавьте текст, чтобы AI мог отвечать по материалам компании." icon="knowledge">
          <template #actions><button type="button" @click="uploadInput?.click()">Загрузить документ</button></template>
        </UiEmptyState>
      </section>
    </section>

    <section v-else class="panel brain-placeholder">
      <p class="eyebrow">{{ activeTab }}</p>
      <h2>{{ activeTab === "collections" ? "Коллекции" : activeTab === "agents" ? "AI-агенты" : "Настройки" }}</h2>
      <p class="hint">Раздел находится в разработке.</p>
    </section>
  </section>
</template>
