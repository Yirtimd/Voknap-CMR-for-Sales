<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import voknapLogo from "../assets/voknap-logo.png";
import GlobalAgentSidebar from "../components/crm/GlobalAgentSidebar.vue";
import { crmStore } from "../stores/crm";

const router = useRouter();
const route = useRoute();

const navItems = [
  { to: "/home", label: "Home" },
  { to: "/companies", label: "Companies" },
  { to: "/deals", label: "Deals" },
  { to: "/tasks", label: "Tasks" },
  { to: "/inbox", label: "Inbox" },
  { to: "/knowledge", label: "Knowledge" },
  { to: "/analytics", label: "Analytics" },
  { to: "/settings", label: "Settings" }
];

const pageTitle = computed(() => String(route.meta.title ?? "AI Sales Workspace"));
const pageEyebrow = computed(() => String(route.meta.eyebrow ?? "Workspace"));
const isAgentOpen = ref(false);

onMounted(() => {
  void crmStore.refreshAll();
});

function logout() {
  crmStore.logout();
  void router.push("/login");
}
</script>

<template>
  <main class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark"><img :src="voknapLogo" alt="Voknap" /></span>
      </div>

      <nav class="nav">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to">{{ item.label }}</RouterLink>
      </nav>

      <button class="secondary" type="button" @click="logout">Выйти</button>
    </aside>

    <section class="content">
      <header class="topbar">
        <div>
          <p class="eyebrow">{{ pageEyebrow }}</p>
          <h1>{{ pageTitle }}</h1>
        </div>
        <button type="button" class="secondary" @click="crmStore.refreshAll">Обновить</button>
      </header>

      <div v-if="crmStore.error.value" class="alert error">{{ crmStore.error.value }}</div>
      <div v-if="crmStore.ok.value" class="alert success">{{ crmStore.ok.value }}</div>

      <RouterView />
    </section>

    <button
      v-if="!isAgentOpen"
      class="agent-edge"
      type="button"
      aria-label="Открыть AI агента"
      @click="isAgentOpen = true"
    >
      <span>‹</span>
    </button>

    <GlobalAgentSidebar :open="isAgentOpen" @close="isAgentOpen = false" />
  </main>
</template>
