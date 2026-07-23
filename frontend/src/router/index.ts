import { createRouter, createWebHistory, type RouteLocationNormalized } from "vue-router";

import AppLayout from "../layouts/AppLayout.vue";
import AutomationPage from "../pages/AutomationPage.vue";
import CompaniesPage from "../pages/CompaniesPage.vue";
import DealsPage from "../pages/DealsPage.vue";
import HomePage from "../pages/HomePage.vue";
import InboxPage from "../pages/InboxPage.vue";
import LoginPage from "../pages/LoginPage.vue";
import InvitationAcceptPage from "../pages/InvitationAcceptPage.vue";
import KnowledgePage from "../pages/KnowledgePage.vue";
import LeadsPage from "../pages/LeadsPage.vue";
import LifecyclePage from "../pages/LifecyclePage.vue";
import AnalyticsPage from "../pages/AnalyticsPage.vue";
import SettingsPage from "../pages/SettingsPage.vue";
import TasksPage from "../pages/TasksPage.vue";
import TeamManagementPage from "../pages/TeamManagementPage.vue";
import { crmStore } from "../stores/crm";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginPage },
    { path: "/accept-invitation", name: "accept-invitation", component: InvitationAcceptPage },
    {
      path: "/",
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        { path: "", redirect: "/home" },
        { path: "home", name: "home", component: HomePage, meta: { title: "Главная", eyebrow: "Рабочий день" } },
        { path: "companies", name: "companies", component: CompaniesPage, meta: { title: "Компании", eyebrow: "Клиентская база" } },
        { path: "companies/:id", redirect: (to) => ({ path: "/companies", query: { company: String(to.params.id), ...(typeof to.query.tab === "string" ? { tab: to.query.tab } : {}) } }) },
        { path: "leads", name: "leads", component: LeadsPage, meta: { title: "Лиды", eyebrow: "Входящий спрос" } },
        {
          path: "crm/:entity(contacts|leads|deals|tasks|notes)",
          name: "lifecycle",
          component: LifecyclePage,
          meta: { title: "Архив и корзина", eyebrow: "Администрирование CRM" }
        },
        { path: "deals", name: "deals", component: DealsPage, meta: { title: "Сделки", eyebrow: "Воронка продаж" } },
        { path: "tasks", name: "tasks", component: TasksPage, meta: { title: "Задачи", eyebrow: "Рабочий процесс" } },
        { path: "automation", name: "automation", component: AutomationPage, meta: { title: "Автоматизация", eyebrow: "Процессы и контроль" } },
        { path: "team", name: "team", component: TeamManagementPage, meta: { title: "Управление командой", eyebrow: "Люди и назначения" } },
        { path: "inbox", name: "inbox", component: InboxPage, meta: { title: "Входящие", eyebrow: "Коммуникации" } },
        { path: "knowledge", name: "knowledge", component: KnowledgePage, meta: { title: "База знаний", eyebrow: "Знания компании" } },
        { path: "analytics", name: "analytics", component: AnalyticsPage, meta: { title: "Аналитика", eyebrow: "Результаты продаж" } },
        { path: "settings", name: "settings", component: SettingsPage, meta: { title: "Настройки", eyebrow: "Управление системой" } },
        { path: "dashboard", redirect: "/home" },
        { path: "timeline", redirect: "/companies" },
        { path: "agent", redirect: "/home" },
        { path: "connectors", redirect: "/settings" },
        { path: "templates", redirect: "/settings" },
        { path: "production", redirect: "/settings" }
      ]
    }
  ]
});

router.beforeEach((to: RouteLocationNormalized) => {
  if (to.meta.requiresAuth && !crmStore.isAuthed.value) {
    return "/login";
  }

  if (to.name === "login" && crmStore.isAuthed.value) {
    return "/home";
  }

  return true;
});
