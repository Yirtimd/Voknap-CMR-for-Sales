import { createRouter, createWebHistory, type RouteLocationNormalized } from "vue-router";

import AppLayout from "../layouts/AppLayout.vue";
import CompaniesPage from "../pages/CompaniesPage.vue";
import DealsPage from "../pages/DealsPage.vue";
import HomePage from "../pages/HomePage.vue";
import InboxPage from "../pages/InboxPage.vue";
import LoginPage from "../pages/LoginPage.vue";
import KnowledgePage from "../pages/KnowledgePage.vue";
import LeadsPage from "../pages/LeadsPage.vue";
import AnalyticsPage from "../pages/AnalyticsPage.vue";
import SettingsPage from "../pages/SettingsPage.vue";
import TasksPage from "../pages/TasksPage.vue";
import { crmStore } from "../stores/crm";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginPage },
    {
      path: "/",
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        { path: "", redirect: "/home" },
        { path: "home", name: "home", component: HomePage, meta: { title: "Home", eyebrow: "Daily workspace" } },
        { path: "companies", name: "companies", component: CompaniesPage, meta: { title: "Companies", eyebrow: "Company-first CRM" } },
        { path: "companies/:id", redirect: (to) => ({ path: "/companies", query: { company: String(to.params.id), ...(typeof to.query.tab === "string" ? { tab: to.query.tab } : {}) } }) },
        { path: "leads", name: "leads", component: LeadsPage, meta: { title: "Leads", eyebrow: "Demand pipeline" } },
        { path: "deals", name: "deals", component: DealsPage, meta: { title: "Deals", eyebrow: "Pipeline" } },
        { path: "tasks", name: "tasks", component: TasksPage, meta: { title: "Tasks", eyebrow: "Execution" } },
        { path: "inbox", name: "inbox", component: InboxPage, meta: { title: "Inbox", eyebrow: "Communication Hub" } },
        { path: "knowledge", name: "knowledge", component: KnowledgePage, meta: { title: "Workspace Knowledge", eyebrow: "General RAG" } },
        { path: "analytics", name: "analytics", component: AnalyticsPage, meta: { title: "Analytics", eyebrow: "Revenue intelligence" } },
        { path: "settings", name: "settings", component: SettingsPage, meta: { title: "Settings", eyebrow: "Administration" } },
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
