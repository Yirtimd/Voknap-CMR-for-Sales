<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import voknapLogo from "../assets/voknap-logo.png";
import GlobalAgentSidebar from "../components/crm/GlobalAgentSidebar.vue";
import { crmStore } from "../stores/crm";

const router = useRouter();
const route = useRoute();

const navItems = [
  { to: "/home", label: "Home", icon: "▣" },
  { to: "/companies", label: "Companies", icon: "▥" },
  { to: "/leads", label: "Leads", icon: "◎" },
  { to: "/deals", label: "Deals", icon: "$" },
  { to: "/tasks", label: "Tasks", icon: "☑" },
  { to: "/inbox", label: "Inbox", icon: "✉" },
  { to: "/knowledge", label: "Workspace Knowledge", icon: "◉" },
  { to: "/analytics", label: "Analytics", icon: "▥" },
  { to: "/settings", label: "Settings", icon: "⚙" }
];

const pageTitle = computed(() => String(route.meta.title ?? "AI Sales Workspace"));
const pageEyebrow = computed(() => String(route.meta.eyebrow ?? "Workspace"));
const isHome = computed(() => route.path === "/home");
const isTasks = computed(() => route.path === "/tasks");
const isAgentOpen = ref(false);
const sidebarMode = ref<"full" | "compact" | "hidden">(
  (localStorage.getItem("cmr_sidebar_mode") as "full" | "compact" | "hidden" | null) ?? "full"
);
const searchQuery = ref("");
const activePanel = ref<"search" | "new" | "notifications" | "profile" | "menu" | null>(null);

const searchResults = computed(() => {
  const needle = searchQuery.value.trim().toLowerCase();
  if (needle.length < 2) return [];
  const companies = crmStore.companies.value
    .filter((item) => [item.name, item.industry, item.website].some((value) => String(value ?? "").toLowerCase().includes(needle)))
    .map((item) => ({ id: `company-${item.id}`, type: "Company", title: item.name, meta: item.industry ?? "Company", to: `/companies/${item.id}` }));
  const deals = crmStore.deals.value
    .filter((item) => [item.title, item.next_step, item.expected_next_event].some((value) => String(value ?? "").toLowerCase().includes(needle)))
    .map((item) => ({ id: `deal-${item.id}`, type: "Deal", title: item.title, meta: crmStore.money(item.amount), to: `/deals?deal=${item.id}` }));
  const leads = crmStore.leads.value
    .filter((item) => [item.title, item.source, item.status].some((value) => String(value ?? "").toLowerCase().includes(needle)))
    .map((item) => ({ id: `lead-${item.id}`, type: "Lead", title: item.title, meta: item.source ?? item.status, to: "/leads" }));
  const tasks = crmStore.tasks.value
    .filter((item) => [item.title, item.description].some((value) => String(value ?? "").toLowerCase().includes(needle)))
    .map((item) => ({ id: `task-${item.id}`, type: "Task", title: item.title, meta: item.due_at ? new Date(item.due_at).toLocaleString("ru-RU") : "No due date", to: "/tasks" }));
  return [...companies, ...leads, ...deals, ...tasks].slice(0, 10);
});

const notifications = computed(() => {
  const now = Date.now();
  const overdue = crmStore.tasks.value
    .filter((task) => !task.done_at && task.due_at && new Date(task.due_at).getTime() < now)
    .map((task) => ({ id: `task-${task.id}`, tone: "danger", title: "Просрочена задача", text: task.title, to: "/tasks" }));
  const risks = crmStore.deals.value
    .filter((deal) => deal.status === "open" && deal.risk_level === "high")
    .map((deal) => ({ id: `deal-${deal.id}`, tone: "warning", title: "Сделка высокого риска", text: deal.title, to: `/deals?deal=${deal.id}` }));
  const incoming = crmStore.communicationEvents.value
    .filter((event) => event.direction === "inbound" && ["new", "received", "unread"].includes(event.status))
    .map((event) => ({ id: `event-${event.id}`, tone: "info", title: "Новое входящее", text: event.subject, to: "/inbox" }));
  return [...overdue, ...risks, ...incoming].slice(0, 10);
});

const initials = computed(() => {
  const name = crmStore.me.value?.full_name ?? crmStore.activeTenant.value?.name ?? "User";
  return name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
});

function keyboardShortcut(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    activePanel.value = "search";
    requestAnimationFrame(() => document.querySelector<HTMLInputElement>(".home-search input")?.focus());
  }
  if (event.key === "Escape") activePanel.value = null;
}

onMounted(async () => {
  await Promise.allSettled([crmStore.refreshAll(), crmStore.refreshMe(), crmStore.refreshCommunication()]);
  window.addEventListener("keydown", keyboardShortcut);
});

onBeforeUnmount(() => window.removeEventListener("keydown", keyboardShortcut));

function togglePanel(panel: Exclude<typeof activePanel.value, null>) {
  activePanel.value = activePanel.value === panel ? null : panel;
}

function navigate(to: string) {
  activePanel.value = null;
  searchQuery.value = "";
  void router.push(to);
}

function logout() {
  crmStore.logout();
  void router.push("/login");
}

function setSidebarMode(mode: "full" | "compact" | "hidden") {
  sidebarMode.value = mode;
  localStorage.setItem("cmr_sidebar_mode", mode);
}

function openTaskCreate() {
  void router.replace({ path: "/tasks", query: { ...route.query, create: "1" } });
}
</script>

<template>
  <main class="app-shell" :class="[`sidebar-${sidebarMode}`, { 'agent-open': isAgentOpen, 'tasks-workspace-active': isTasks }]">
    <aside class="sidebar">
      <div class="sidebar-controls" aria-label="Sidebar mode">
        <button type="button" :class="{ active: sidebarMode === 'full' }" aria-label="Полный сайдбар" @click="setSidebarMode('full')">▰</button>
        <button type="button" :class="{ active: sidebarMode === 'compact' }" aria-label="Компактный сайдбар" @click="setSidebarMode('compact')">▌</button>
        <button type="button" :class="{ active: sidebarMode === 'hidden' }" aria-label="Скрыть сайдбар" @click="setSidebarMode('hidden')">—</button>
      </div>
      <div class="brand">
        <span class="brand-mark"><img :src="voknapLogo" alt="Voknap" /></span>
      </div>

      <nav class="nav">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" :data-label="item.label"><span>{{ item.icon }}</span><b>{{ item.label }}</b></RouterLink>
      </nav>

      <button class="secondary" type="button" @click="logout">Выйти</button>
    </aside>

    <div v-if="sidebarMode === 'hidden'" class="sidebar-hover-zone" aria-hidden="true"></div>

    <section class="content">
      <header v-if="isHome" class="topbar home-topbar">
        <h1>Home</h1>
        <label class="home-search" aria-label="Поиск">
          <span>⌕</span>
          <input v-model="searchQuery" type="search" placeholder="Search deals, companies, tasks..." @focus="activePanel = 'search'" />
          <kbd>⌘K</kbd>
          <section v-if="activePanel === 'search'" class="top-popover search-popover">
            <p v-if="searchQuery.trim().length < 2" class="popover-empty">Введите минимум 2 символа</p>
            <button v-for="item in searchResults" :key="item.id" type="button" class="popover-row" @click="navigate(item.to)">
              <span>{{ item.type }}</span><div><strong>{{ item.title }}</strong><small>{{ item.meta }}</small></div>
            </button>
            <p v-if="searchQuery.trim().length >= 2 && !searchResults.length" class="popover-empty">Ничего не найдено</p>
          </section>
        </label>
        <div class="home-top-actions">
          <div class="top-action-wrap">
            <button type="button" class="secondary home-new-button" @click="togglePanel('new')"><span>+</span> New <span>⌄</span></button>
            <section v-if="activePanel === 'new'" class="top-popover action-popover">
              <button type="button" @click="navigate('/companies?create=1')">New company</button>
              <button type="button" @click="navigate('/leads')">New lead</button>
              <button type="button" @click="navigate('/deals?create=1')">New deal</button>
              <button type="button" @click="navigate('/tasks?create=1')">New task</button>
              <button type="button" @click="navigate('/inbox')">Incoming event</button>
            </section>
          </div>
          <div class="top-action-wrap">
            <button type="button" class="secondary home-bell" aria-label="Уведомления" @click="togglePanel('notifications')"><span>♧</span><b v-if="notifications.length">{{ notifications.length }}</b></button>
            <section v-if="activePanel === 'notifications'" class="top-popover notification-popover">
              <header><strong>Notifications</strong><small>{{ notifications.length }}</small></header>
              <button v-for="item in notifications" :key="item.id" type="button" class="popover-row" @click="navigate(item.to)">
                <i :class="item.tone"></i><div><strong>{{ item.title }}</strong><small>{{ item.text }}</small></div>
              </button>
              <p v-if="!notifications.length" class="popover-empty">Новых уведомлений нет</p>
            </section>
          </div>
          <div class="top-action-wrap">
            <button type="button" class="secondary home-avatar" aria-label="Профиль" @click="togglePanel('profile')">{{ initials }}</button>
            <section v-if="activePanel === 'profile'" class="top-popover profile-popover">
              <strong>{{ crmStore.me.value?.full_name ?? "User" }}</strong>
              <small>{{ crmStore.me.value?.email }}</small>
              <small>{{ crmStore.me.value?.role }} · {{ crmStore.activeTenant.value?.name }}</small>
              <button type="button" @click="navigate('/settings')">Profile settings</button>
            </section>
          </div>
          <div class="top-action-wrap">
            <button type="button" class="secondary home-caret" aria-label="Меню" @click="togglePanel('menu')">⌄</button>
            <section v-if="activePanel === 'menu'" class="top-popover action-popover menu-popover">
              <button type="button" @click="navigate('/settings')">Workspace settings</button>
              <button type="button" @click="isAgentOpen = true; activePanel = null">AI Agent</button>
              <button type="button" class="danger-item" @click="logout">Выйти</button>
            </section>
          </div>
        </div>
      </header>

      <header v-else class="topbar" :class="{ 'tasks-topbar': isTasks }">
        <div>
          <p class="eyebrow">{{ pageEyebrow }}</p>
          <h1>{{ pageTitle }}</h1>
        </div>
        <div v-if="isTasks" class="tasks-top-actions">
          <button type="button" class="secondary tasks-ai-inbox" @click="navigate('/inbox')"><span>✦</span> AI Inbox <b>{{ notifications.length }}</b></button>
          <button type="button" class="tasks-new-button" @click="openTaskCreate"><span>＋</span> New Task</button>
          <button type="button" class="secondary tasks-refresh" @click="crmStore.refreshAll"><span>⟳</span> Обновить</button>
          <button type="button" class="secondary tasks-more" aria-label="Дополнительные действия">⋮</button>
        </div>
        <button v-else type="button" class="secondary" @click="crmStore.refreshAll">Обновить</button>
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

<style scoped>
.home-search, .top-action-wrap { position: relative; }
.top-popover { position: absolute; z-index: 80; top: calc(100% + 8px); right: 0; width: 280px; overflow: hidden; border: 1px solid var(--line); border-radius: 10px; padding: 8px; background: var(--surface-solid); box-shadow: 0 16px 40px rgb(0 0 0 / 14%); }
.search-popover { right: auto; left: 0; width: 100%; min-width: 390px; }
.top-popover button { width: 100%; justify-content: flex-start; border: 0; padding: 10px; color: var(--text); background: transparent; text-align: left; }
.top-popover button:hover { background: var(--surface-muted); }
.popover-row { display: flex; align-items: center; gap: 10px; }
.popover-row > span { flex: 0 0 62px; color: var(--brand); font-size: 10px; font-weight: 800; text-transform: uppercase; }
.popover-row > div { display: grid; min-width: 0; gap: 2px; }
.popover-row small, .profile-popover small { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.popover-empty { margin: 0; padding: 14px 10px; color: var(--muted); text-align: center; }
.notification-popover header { display: flex; justify-content: space-between; padding: 8px 10px; }
.popover-row i { width: 8px; height: 8px; border-radius: 50%; background: var(--brand); }
.popover-row i.danger { background: var(--danger); }
.popover-row i.warning { background: var(--warning); }
.profile-popover { display: grid; gap: 6px; padding: 14px; }
.profile-popover button { margin-top: 6px; }
.top-popover .danger-item { color: var(--danger); }
.tasks-topbar { min-height: 82px; background: rgba(255, 255, 255, 0.9); }
.tasks-topbar h1 { margin: 2px 0 0; font-size: 28px; line-height: 34px; letter-spacing: -0.025em; }
.tasks-topbar .eyebrow { margin: 0; font-size: 10px; line-height: 14px; letter-spacing: 0.08em; text-transform: uppercase; }
.tasks-top-actions { display: flex; align-items: center; gap: 8px; }
.tasks-top-actions button { height: 38px; border-radius: 8px; padding: 0 13px; font-size: 13px; white-space: nowrap; }
.tasks-top-actions button span { font-size: 15px; }
.tasks-top-actions .tasks-ai-inbox { gap: 7px; color: #172033; }
.tasks-ai-inbox span { color: #7656e8; }
.tasks-ai-inbox b { display: grid; place-items: center; min-width: 22px; height: 22px; border-radius: 999px; padding: 0 6px; color: #0b72e7; background: #edf5ff; font-size: 10px; }
.tasks-top-actions .tasks-new-button { gap: 7px; border-color: #0b72e7; background: #0b72e7; }
.tasks-top-actions .tasks-refresh { gap: 7px; color: #172033; }
.tasks-top-actions .tasks-more { width: 38px; padding: 0; color: #172033; font-size: 18px; }
.app-shell.tasks-workspace-active { background: #f6f8fb; }
.tasks-workspace-active .content { width: min(1600px, 100%); padding: 20px 24px 32px; }
.tasks-workspace-active .topbar { margin: -20px -24px 20px; padding: 18px 24px; }
@media (max-width: 760px) { .tasks-top-actions .tasks-ai-inbox, .tasks-top-actions .tasks-refresh { display: none; } .tasks-topbar h1 { font-size: 23px; } }
@media (max-width: 920px) { .app-shell.tasks-workspace-active { grid-template-columns: 1fr; } .tasks-workspace-active .content { padding: 18px 14px 28px; } .tasks-workspace-active .topbar { margin: -18px -14px 16px; padding: 16px 14px 12px; } }
@media (max-width: 760px) { .search-popover { min-width: 280px; } .top-popover { right: auto; left: 0; } }
</style>
