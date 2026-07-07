<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import voknapLogo from "../assets/voknap-logo.png";
import GlobalAgentSidebar from "../components/crm/GlobalAgentSidebar.vue";
import { crmStore } from "../stores/crm";

const router = useRouter();
const route = useRoute();

const navItems = [
  { to: "/home", label: "Home", icon: "▣" },
  { to: "/companies", label: "Companies", icon: "▥" },
  { to: "/deals", label: "Deals", icon: "$" },
  { to: "/tasks", label: "Tasks", icon: "☑" },
  { to: "/inbox", label: "Inbox", icon: "✉" },
  { to: "/knowledge", label: "Company Brain", icon: "◉" },
  { to: "/analytics", label: "Analytics", icon: "▥" },
  { to: "/settings", label: "Settings", icon: "⚙" }
];

const pageTitle = computed(() => String(route.meta.title ?? "AI Sales Workspace"));
const pageEyebrow = computed(() => String(route.meta.eyebrow ?? "Workspace"));
const isHome = computed(() => route.path === "/home");
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
  <main class="app-shell" :class="{ 'agent-open': isAgentOpen }">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark"><img :src="voknapLogo" alt="Voknap" /></span>
      </div>

      <nav class="nav">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to"><span>{{ item.icon }}</span>{{ item.label }}</RouterLink>
      </nav>

      <button class="secondary" type="button" @click="logout">Выйти</button>
    </aside>

    <section class="content">
      <header v-if="isHome" class="topbar home-topbar">
        <h1>Home</h1>
        <label class="home-search" aria-label="Поиск">
          <span>⌕</span>
          <input type="search" placeholder="Search deals, companies, tasks..." />
          <kbd>⌘K</kbd>
        </label>
        <div class="home-top-actions">
          <button type="button" class="secondary home-new-button"><span>+</span> New <span>⌄</span></button>
          <button type="button" class="secondary home-bell" aria-label="Уведомления"><span>♧</span><b>3</b></button>
          <button type="button" class="secondary home-avatar" aria-label="Профиль">DM</button>
          <button type="button" class="secondary home-caret" aria-label="Меню">⌄</button>
        </div>
      </header>

      <header v-else class="topbar">
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

    <div v-if="isAgentOpen" class="agent-backdrop" @click="isAgentOpen = false"></div>
    <GlobalAgentSidebar :open="isAgentOpen" @close="isAgentOpen = false" />
  </main>
</template>
