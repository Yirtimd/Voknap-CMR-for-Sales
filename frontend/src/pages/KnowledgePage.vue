<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { crmStore } from "../stores/crm";

const activeTab = ref<"chat" | "documents" | "collections" | "agents" | "settings">("chat");

const suggestedQuestions = [
  "How do we qualify leads?",
  "Where is pricing stored?",
  "Explain onboarding.",
  "How do we work with enterprise clients?",
  "Show company policies.",
  "Find contract template."
];

const relatedKnowledge = [
  { title: "Lead Qualification", children: ["Sales Script", "Pricing", "Discovery", "Proposal"] },
  { title: "Enterprise Sales", children: ["Security review", "Stakeholders", "Commercial terms"] }
];

const aiActions = ["Create task", "Create deal checklist", "Open document", "Summarize", "Explain simply", "Generate SOP", "Send to Agent"];

const confidence = computed(() => {
  const citations = crmStore.knowledgeAnswer.value?.citations ?? [];
  if (!citations.length) return 0;
  return Math.min(99, Math.max(72, Math.round(citations[0].score * 100)));
});

const sourceSummary = computed(() => {
  const count = new Set((crmStore.knowledgeAnswer.value?.citations ?? []).map((item) => item.document_id)).size;
  if (!count) return "Ask a question to see how the answer was built.";
  return `Answer built from ${count} general workspace ${count === 1 ? "document" : "documents"}.`;
});

function askSuggested(question: string) {
  crmStore.knowledgeAskForm.value.question = question;
  void crmStore.askKnowledge();
}

function relevance(score: number) {
  return `${Math.min(99, Math.max(61, Math.round(score * 100)))}% relevance`;
}

onMounted(() => {
  void crmStore.refreshKnowledge();
});
</script>

<template>
  <section class="brain-page">
    <nav class="brain-tabs" aria-label="Workspace Knowledge sections">
      <button type="button" :class="{ active: activeTab === 'chat' }" @click="activeTab = 'chat'">Chat</button>
      <button type="button" :class="{ active: activeTab === 'documents' }" @click="activeTab = 'documents'">Documents</button>
      <button type="button" :class="{ active: activeTab === 'collections' }" @click="activeTab = 'collections'">Collections</button>
      <button type="button" :class="{ active: activeTab === 'agents' }" @click="activeTab = 'agents'">AI Agents</button>
      <button type="button" :class="{ active: activeTab === 'settings' }" @click="activeTab = 'settings'">Settings</button>
    </nav>

    <section v-if="activeTab === 'chat'" class="brain-chat-layout">
      <div class="brain-main">
        <section class="brain-ask">
          <p class="eyebrow">Workspace Knowledge</p>
          <h2>Good afternoon, Dmitry.</h2>
          <p>What would you like to know?</p>

          <form class="brain-question" @submit.prevent="crmStore.askKnowledge()">
            <textarea
              v-model="crmStore.knowledgeAskForm.value.question"
              rows="3"
              placeholder="Ask about sales, policies, onboarding, pricing, contracts..."
            ></textarea>
            <button type="submit">Ask</button>
          </form>

          <div class="suggested-grid" aria-label="Suggested questions">
            <button v-for="question in suggestedQuestions" :key="question" type="button" @click="askSuggested(question)">
              {{ question }}
            </button>
          </div>
        </section>

        <section v-if="crmStore.knowledgeAnswer.value" class="panel brain-answer">
          <div class="brain-answer-head">
            <div>
              <p class="eyebrow">Answer</p>
              <h2>General knowledge answer</h2>
            </div>
            <div class="confidence-meter">
              <span>Confidence</span>
              <strong>{{ confidence }}%</strong>
            </div>
          </div>

          <p class="answer-text">{{ crmStore.knowledgeAnswer.value.answer }}</p>

          <div class="reasoning-block">
            <span>Reasoning</span>
            <p>{{ sourceSummary }}</p>
          </div>

          <div class="ai-actions">
            <button v-for="action in aiActions" :key="action" type="button" class="secondary">{{ action }}</button>
          </div>

          <div class="source-list">
            <h3>Sources</h3>
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
              <button type="button" class="secondary">Open</button>
            </article>
          </div>
        </section>
      </div>

      <aside class="brain-rail">
        <section class="panel compact-panel">
          <h2>Related knowledge</h2>
          <div v-for="group in relatedKnowledge" :key="group.title" class="knowledge-branch">
            <strong>{{ group.title }}</strong>
            <span v-for="child in group.children" :key="child">{{ child }}</span>
          </div>
        </section>

        <section class="panel compact-panel">
          <h2>Documents</h2>
          <div v-for="document in crmStore.knowledgeDocuments.value.slice(0, 4)" :key="document.id" class="document-mini-row">
            <div>
              <strong>{{ document.title }}</strong>
              <small>{{ document.chunks_count }} knowledge pieces</small>
            </div>
            <span :class="['status-pill', document.status]">{{ document.status }}</span>
          </div>
          <p v-if="!crmStore.knowledgeDocuments.value.length" class="empty">No documents connected yet.</p>
        </section>
      </aside>
    </section>

    <section v-else-if="activeTab === 'documents'" class="documents-workspace">
      <section class="panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Workspace Memory</p>
            <h2>Documents</h2>
          </div>
          <button type="button" @click="crmStore.createKnowledgeDocument">Upload</button>
        </div>

        <form class="document-upload-form" @submit.prevent="crmStore.createKnowledgeDocument">
          <label>Title<input v-model="crmStore.knowledgeDocumentForm.value.title" /></label>
          <label>Collection<input v-model="crmStore.knowledgeDocumentForm.value.source_type" /></label>
          <label class="wide-field">Content<textarea v-model="crmStore.knowledgeDocumentForm.value.text" class="large-textarea"></textarea></label>
          <button type="submit">Add document</button>
        </form>
      </section>

      <section class="panel">
        <article v-for="document in crmStore.knowledgeDocuments.value" :key="document.id" class="document-row">
          <div>
            <strong>{{ document.title }}</strong>
            <small>{{ document.chunks_count }} knowledge pieces · updated {{ new Date(document.created_at).toLocaleDateString() }}</small>
          </div>
          <span :class="['status-pill', document.status]">{{ document.status }}</span>
        </article>
        <p v-if="!crmStore.knowledgeDocuments.value.length" class="empty">Documents will appear here after upload.</p>
      </section>
    </section>

    <section v-else class="panel brain-placeholder">
      <p class="eyebrow">{{ activeTab }}</p>
      <h2>{{ activeTab === "collections" ? "Collections" : activeTab === "agents" ? "AI Agents" : "Settings" }}</h2>
      <p class="hint">This area is reserved for the next Workspace Knowledge screen.</p>
    </section>
  </section>
</template>
