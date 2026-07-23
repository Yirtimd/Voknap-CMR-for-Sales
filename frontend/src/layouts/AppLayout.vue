<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import voknapLogo from "../assets/voknap-logo.png";
import GlobalAgentSidebar from "../components/crm/GlobalAgentSidebar.vue";
import { crmStore } from "../stores/crm";

const router = useRouter();
const route = useRoute();

const navItems = [
  { to: "/home", label: "Главная", icon: "home" },
  { to: "/companies", label: "Компании", icon: "companies" },
  { to: "/leads", label: "Лиды", icon: "leads" },
  { to: "/deals", label: "Сделки", icon: "deals" },
  { to: "/tasks", label: "Задачи", icon: "tasks" },
  { to: "/automation", label: "Автоматизация", icon: "automation" },
  { to: "/crm/contacts", label: "Архив и корзина", icon: "records" },
  { to: "/team", label: "Управление командой", icon: "team" },
  { to: "/inbox", label: "Входящие", icon: "inbox" },
  { to: "/knowledge", label: "База знаний", icon: "knowledge" },
  { to: "/analytics", label: "Аналитика", icon: "analytics" },
  { to: "/settings", label: "Настройки", icon: "settings" }
];

const navIconPaths: Record<string, string> = {
  home: "m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1V10Z",
  companies: "M4 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16M2 21h20M8 7h4M8 11h4M8 15h4M17 8h3M17 12h3M17 16h3",
  leads: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
  deals: "M3 7h18v12H3zM3 7l3-4h12l3 4M8 12h8",
  tasks: "M9 11 11 13l4-4M9 17l2 2 4-4M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z",
  automation: "M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83M9 12a3 3 0 1 0 6 0 3 3 0 0 0-6 0Z",
  records: "M4 5.5C4 4.12 7.58 3 12 3s8 1.12 8 2.5S16.42 8 12 8 4 6.88 4 5.5Zm0 0v6C4 12.88 7.58 14 12 14s8-1.12 8-2.5v-6M4 11.5v7C4 19.88 7.58 21 12 21s8-1.12 8-2.5v-7",
  team: "M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M8.5 13a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM22 21v-2a4 4 0 0 0-3-3.87M16 5.13a4 4 0 0 1 0 7.75",
  inbox: "M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Zm-2 3 10 6L22 7",
  knowledge: "M4 5.5A2.5 2.5 0 0 1 6.5 3H12v17H6.5A2.5 2.5 0 0 0 4 22.5v-17ZM20 5.5A2.5 2.5 0 0 0 17.5 3H12v17h5.5a2.5 2.5 0 0 1 2.5 2.5v-17Z",
  analytics: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  settings: "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.12 2.12-.06-.06A1.7 1.7 0 0 0 15.74 18a1.7 1.7 0 0 0-1.04 1.56V20h-3v-.44A1.7 1.7 0 0 0 10.66 18a1.7 1.7 0 0 0-1.88.34l-.06.06-2.12-2.12.06-.06A1.7 1.7 0 0 0 7 14.34a1.7 1.7 0 0 0-1.56-1.04H5v-3h.44A1.7 1.7 0 0 0 7 9.26a1.7 1.7 0 0 0-.34-1.88L6.6 7.32 8.72 5.2l.06.06A1.7 1.7 0 0 0 10.66 5a1.7 1.7 0 0 0 1.04-1.56V3h3v.44A1.7 1.7 0 0 0 15.74 5a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.12 2.12-.06.06A1.7 1.7 0 0 0 19.4 8.66a1.7 1.7 0 0 0 1.56 1.04h.44v3h-.44A1.7 1.7 0 0 0 19.4 15Z"
};

const pageTitle = computed(() => String(route.meta.title ?? "Рабочее пространство"));
const pageEyebrow = computed(() => String(route.meta.eyebrow ?? "CRM"));
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
    .map((item) => ({ id: `company-${item.id}`, type: "Компания", title: item.name, meta: item.industry ?? "Компания", to: `/companies/${item.id}` }));
  const deals = crmStore.deals.value
    .filter((item) => [item.title, item.next_step, item.expected_next_event].some((value) => String(value ?? "").toLowerCase().includes(needle)))
    .map((item) => ({ id: `deal-${item.id}`, type: "Сделка", title: item.title, meta: crmStore.money(item.amount), to: `/deals?deal=${item.id}` }));
  const leads = crmStore.leads.value
    .filter((item) => [item.title, item.source, item.status].some((value) => String(value ?? "").toLowerCase().includes(needle)))
    .map((item) => ({ id: `lead-${item.id}`, type: "Лид", title: item.title, meta: item.source ?? item.status, to: `/leads?record=${item.id}` }));
  const tasks = crmStore.tasks.value
    .filter((item) => [item.title, item.description].some((value) => String(value ?? "").toLowerCase().includes(needle)))
    .map((item) => ({ id: `task-${item.id}`, type: "Задача", title: item.title, meta: item.due_at ? new Date(item.due_at).toLocaleString("ru-RU") : "Без срока", to: `/tasks?record=${item.id}` }));
  const contacts = crmStore.contacts.value
    .filter((item) => [item.name, item.email, item.phone, item.company_name].some((value) => String(value ?? "").toLowerCase().includes(needle)))
    .map((item) => ({ id: `contact-${item.id}`, type: "Контакт", title: item.name, meta: item.company_name ?? item.email ?? "Контакт", to: `/leads?contact=${item.id}` }));
  return [...companies, ...contacts, ...leads, ...deals, ...tasks].slice(0, 10);
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
  const name = crmStore.me.value?.full_name ?? crmStore.activeTenant.value?.name ?? "Пользователь";
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
    <aside class="sidebar" aria-label="Основная навигация">
      <div class="sidebar-controls" aria-label="Режим боковой панели">
        <button type="button" :class="{ active: sidebarMode === 'full' }" aria-label="Полный сайдбар" title="Полный сайдбар" @click="setSidebarMode('full')"><span class="layout-icon layout-icon-full" aria-hidden="true"></span></button>
        <button type="button" :class="{ active: sidebarMode === 'compact' }" aria-label="Компактный сайдбар" title="Компактный сайдбар" @click="setSidebarMode('compact')"><span class="layout-icon layout-icon-compact" aria-hidden="true"></span></button>
        <button type="button" :class="{ active: sidebarMode === 'hidden' }" aria-label="Скрыть сайдбар" title="Скрыть сайдбар" @click="setSidebarMode('hidden')"><span class="layout-icon layout-icon-hidden" aria-hidden="true"></span></button>
      </div>
      <div class="brand">
        <span class="brand-mark"><img :src="voknapLogo" alt="Voknap" /></span>
      </div>

      <nav class="nav">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" :data-label="item.label">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="navIconPaths[item.icon]" /></svg>
          <b>{{ item.label }}</b>
        </RouterLink>
      </nav>

      <button class="secondary" type="button" @click="logout">Выйти</button>
    </aside>

    <div v-if="sidebarMode === 'hidden'" class="sidebar-hover-zone" aria-hidden="true"></div>

    <section class="content">
      <header v-if="isHome" class="topbar home-topbar">
        <label class="home-search" aria-label="Поиск по рабочему пространству">
          <span>⌕</span>
          <input v-model="searchQuery" type="search" placeholder="Поиск сделок, компаний и задач..." @focus="activePanel = 'search'" />
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
            <button type="button" class="secondary home-new-button" @click="togglePanel('new')"><span>+</span> Создать <span>⌄</span></button>
            <section v-if="activePanel === 'new'" class="top-popover action-popover">
              <button type="button" @click="navigate('/companies?create=1')">Новую компанию</button>
              <button type="button" @click="navigate('/leads')">Новый лид</button>
              <button type="button" @click="navigate('/deals?create=1')">Новую сделку</button>
              <button type="button" @click="navigate('/tasks?create=1')">Новую задачу</button>
              <button type="button" @click="navigate('/inbox')">Входящее событие</button>
            </section>
          </div>
          <div class="top-action-wrap">
            <button type="button" class="secondary home-bell" aria-label="Уведомления" @click="togglePanel('notifications')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></svg><b v-if="notifications.length">{{ notifications.length }}</b></button>
            <section v-if="activePanel === 'notifications'" class="top-popover notification-popover">
              <header><strong>Уведомления</strong><small>{{ notifications.length }}</small></header>
              <button v-for="item in notifications" :key="item.id" type="button" class="popover-row" @click="navigate(item.to)">
                <i :class="item.tone"></i><div><strong>{{ item.title }}</strong><small>{{ item.text }}</small></div>
              </button>
              <p v-if="!notifications.length" class="popover-empty">Новых уведомлений нет</p>
            </section>
          </div>
          <div class="top-action-wrap">
            <button type="button" class="secondary home-avatar" aria-label="Профиль" @click="togglePanel('profile')">{{ initials }}</button>
            <section v-if="activePanel === 'profile'" class="top-popover profile-popover">
              <strong>{{ crmStore.me.value?.full_name ?? "Пользователь" }}</strong>
              <small>{{ crmStore.me.value?.email }}</small>
              <small>{{ crmStore.me.value?.role }} · {{ crmStore.activeTenant.value?.name }}</small>
              <button type="button" @click="navigate('/settings')">Настройки профиля</button>
            </section>
          </div>
          <div class="top-action-wrap">
            <button type="button" class="secondary home-caret" aria-label="Меню" @click="togglePanel('menu')">⌄</button>
            <section v-if="activePanel === 'menu'" class="top-popover action-popover menu-popover">
              <button type="button" @click="navigate('/settings')">Настройки рабочего пространства</button>
              <button type="button" @click="isAgentOpen = true; activePanel = null">AI-ассистент</button>
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
          <button type="button" class="secondary tasks-ai-inbox" @click="navigate('/inbox')"><span>✦</span> AI-входящие <b>{{ notifications.length }}</b></button>
          <button type="button" class="tasks-new-button" @click="openTaskCreate"><span>＋</span> Новая задача</button>
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
