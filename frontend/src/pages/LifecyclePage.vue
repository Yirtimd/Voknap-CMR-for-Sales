<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import UiIcon from "../components/ui/UiIcon.vue";
import { ENTITY_CONFIG, ENTITY_TYPES, type LifecycleField } from "../lifecycleConfig";
import { crmStore } from "../stores/crm";
import {
  lifecycleStore,
  type LifecycleRecord,
  type LifecycleState
} from "../stores/lifecycle";
import type { BulkAction, EntityType, FieldChange, Lead } from "../types";

type DrawerMode = "view" | "create" | "edit";

const route = useRoute();
const router = useRouter();
const drawerMode = ref<DrawerMode | null>(null);
const opened = ref<LifecycleRecord | null>(null);
const draft = reactive<Record<string, string | number | null>>({});
const historyRows = ref<FieldChange[]>([]);
const historyOpen = ref(false);
const historyLoading = ref(false);
const localSearch = ref("");
const notice = ref("");
const formError = ref("");
const ownerId = ref("");
const bulkAction = ref<BulkAction>("archive");
const disqualificationReason = ref("");
const conversion = reactive({ stage_id: "", title: "", amount: "", owner_id: "" });
let searchTimer: number | undefined;

const entityType = computed<EntityType>(() => {
  const value = String(route.params.entity ?? "contacts") as EntityType;
  return ENTITY_TYPES.includes(value) ? value : "contacts";
});
const config = computed(() => ENTITY_CONFIG[entityType.value]);
const scope = computed(() => lifecycleStore.state.value);
const records = computed(() => lifecycleStore.records.value);
const selectedIds = computed(() => new Set(lifecycleStore.selected.value.map((item) => item.id)));
const isAllSelected = computed(() => records.value.length > 0 && records.value.every((item) => selectedIds.value.has(item.id)));
const formFields = computed(() => config.value.fields.filter((field) => drawerMode.value === "create" ? field.create : field.edit));
const activeRecord = computed(() => opened.value && records.value.find((item) => item.id === opened.value?.id) || opened.value);
const canMutateOpened = computed(() => Boolean(activeRecord.value && mayEdit(activeRecord.value)));
const mergeSources = computed(() => {
  const target = activeRecord.value;
  if (!target || !config.value.merge) return [];
  const pool = [...records.value, ...crmList(entityType.value)];
  const seen = new Set<string>();
  return pool.filter((item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return item.id !== target.id && item.company_id === target.company_id && !item.is_archived && !item.deleted_at && mayEdit(item);
  });
});
const availableBulkActions = computed<Array<{ value: BulkAction; label: string }>>(() => {
  if (scope.value === "deleted") return [{ value: "restore", label: "Восстановить" }];
  const actions: Array<{ value: BulkAction; label: string }> = scope.value === "archived"
    ? [{ value: "unarchive", label: "Вернуть из архива" }, { value: "delete", label: "Переместить в корзину" }]
    : [{ value: "archive", label: "Архивировать" }, { value: "delete", label: "Переместить в корзину" }];
  if (lifecycleStore.canReassign.value && entityType.value !== "notes") actions.push({ value: "reassign", label: "Сменить ответственного" });
  return actions;
});
const ownerFilterKey = computed(() => entityType.value === "tasks" ? "assigned_to_id" : entityType.value === "notes" ? "author_id" : "owner_id");

watch(entityType, async (value) => {
  closeDrawer();
  lifecycleStore.clearSelected();
  localSearch.value = "";
  lifecycleStore.setQuery({ entityType: value, state: "active", search: "", filters: {}, sort: "created_at", page: 1 });
  await lifecycleStore.load();
  openFromQuery();
}, { immediate: true });

watch(localSearch, (value) => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => {
    void lifecycleStore.load({ search: value.trim(), page: 1 });
  }, 320);
});

watch(availableBulkActions, (items) => {
  if (!items.some((item) => item.value === bulkAction.value)) bulkAction.value = items[0]?.value ?? "archive";
}, { immediate: true });

onMounted(async () => {
  await Promise.allSettled([crmStore.refreshMe(), crmStore.refreshAll()]);
  await lifecycleStore.loadMembers();
  document.addEventListener("keydown", onKeydown);
});
onBeforeUnmount(() => {
  window.clearTimeout(searchTimer);
  document.removeEventListener("keydown", onKeydown);
});

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") closeDrawer();
}

function crmList(type: EntityType): LifecycleRecord[] {
  if (type === "contacts") return crmStore.contacts.value;
  if (type === "leads") return crmStore.leads.value;
  if (type === "deals") return crmStore.deals.value;
  if (type === "tasks") return crmStore.tasks.value;
  return crmStore.notes.value;
}

function mayEdit(record: LifecycleRecord) {
  if (!lifecycleStore.canWrite.value) return false;
  if (crmStore.me.value?.role !== "sales_rep") return true;
  const ownId = "assigned_to_id" in record ? record.assigned_to_id : "owner_id" in record ? record.owner_id : "author_id" in record ? record.author_id : null;
  return ownId === crmStore.me.value.user_id;
}

function entityTitle(record: LifecycleRecord) {
  return String((record as unknown as Record<string, unknown>)[config.value.titleKey] ?? "Без названия");
}

function entityMeta(record: LifecycleRecord) {
  const source = record as unknown as Record<string, unknown>;
  return config.value.subtitleKeys
    .map((key) => formatValue(key, source[key]))
    .filter(Boolean)
    .join(" · ");
}

function formatValue(key: string, value: unknown) {
  if (value === null || value === undefined || value === "") return "";
  if (key === "amount") return crmStore.money(Number(value));
  if (key.endsWith("_at")) {
    const date = new Date(String(value));
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("ru-RU", { dateStyle: "medium", timeStyle: "short" });
  }
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function shortId(value: unknown) {
  const text = String(value ?? "—");
  return text.length > 12 ? `${text.slice(0, 8)}…` : text;
}

function changeEntity(type: EntityType) {
  void router.push(`/crm/${type}`);
}

async function changeScope(value: LifecycleState) {
  if (value === "deleted" && !lifecycleStore.canViewDeleted.value) return;
  lifecycleStore.clearSelected();
  await lifecycleStore.load({ state: value, page: 1 });
}

async function changeSort() {
  await lifecycleStore.load({ page: 1 });
}

async function changeFilter(name: string, value: string) {
  const next = { ...lifecycleStore.filters.value };
  if (value) next[name] = value;
  else delete next[name];
  await lifecycleStore.load({ filters: next, page: 1 });
}

function openCreate() {
  opened.value = null;
  drawerMode.value = "create";
  historyOpen.value = false;
  resetDraft();
}

function openRecord(record: LifecycleRecord) {
  opened.value = record;
  drawerMode.value = "view";
  historyOpen.value = false;
  formError.value = "";
  ownerId.value = recordOwner(record) ?? "";
  void router.replace({ query: { ...route.query, record: record.id } });
}

function openEdit() {
  if (!activeRecord.value) return;
  resetDraft(activeRecord.value);
  drawerMode.value = "edit";
}

function closeDrawer() {
  drawerMode.value = null;
  opened.value = null;
  historyOpen.value = false;
  formError.value = "";
  if (route.query.record) void router.replace({ query: { ...route.query, record: undefined } });
}

function openFromQuery() {
  const id = typeof route.query.record === "string" ? route.query.record : "";
  const record = records.value.find((item) => item.id === id) ?? crmList(entityType.value).find((item) => item.id === id);
  if (record) openRecord(record);
}

function resetDraft(record?: LifecycleRecord) {
  for (const key of Object.keys(draft)) delete draft[key];
  for (const field of config.value.fields) {
    const value = record ? (record as unknown as Record<string, unknown>)[field.key] : defaultValue(field);
    draft[field.key] = toInputValue(field, value);
  }
  formError.value = "";
}

function defaultValue(field: LifecycleField) {
  if (field.key === "company_id") return crmStore.companies.value[0]?.id ?? "";
  if (field.key === "stage_id") return crmStore.allStages.value[0]?.id ?? "";
  if (field.key === "priority") return "normal";
  if (field.key === "status") return "open";
  return "";
}

function toInputValue(field: LifecycleField, value: unknown): string | number {
  if (value === null || value === undefined) return "";
  if (field.kind === "datetime-local") {
    const date = new Date(String(value));
    if (!Number.isNaN(date.getTime())) return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  }
  return typeof value === "number" ? value : String(value);
}

function referenceOptions(field: LifecycleField) {
  const companyId = String(draft.company_id ?? "");
  if (field.reference === "companies") return crmStore.companies.value.map((item) => ({ value: item.id, label: item.name }));
  if (field.reference === "stages") return crmStore.allStages.value.map((item) => ({ value: item.id, label: item.name }));
  if (field.reference === "contacts") return crmStore.contacts.value.filter((item) => !companyId || item.company_id === companyId).map((item) => ({ value: item.id, label: item.name }));
  if (field.reference === "leads") return crmStore.leads.value.filter((item) => !companyId || item.company_id === companyId).map((item) => ({ value: item.id, label: item.title }));
  if (field.reference === "deals") return crmStore.deals.value.filter((item) => !companyId || item.company_id === companyId).map((item) => ({ value: item.id, label: item.title }));
  return [];
}

function payloadFromDraft() {
  const payload: Record<string, unknown> = {};
  for (const field of formFields.value) {
    const value = draft[field.key];
    if (field.kind === "number") payload[field.key] = value === "" || value === null ? null : Number(value);
    else if (field.kind === "datetime-local") payload[field.key] = value ? new Date(String(value)).toISOString() : null;
    else payload[field.key] = value === "" ? null : value;
  }
  return payload;
}

async function saveRecord() {
  formError.value = "";
  if (entityType.value === "notes" && drawerMode.value === "create" && !draft.lead_id && !draft.deal_id) {
    formError.value = "Для заметки выберите лид или сделку.";
    return;
  }
  try {
    if (drawerMode.value === "create") {
      const created = await lifecycleStore.create(entityType.value, payloadFromDraft());
      opened.value = created;
      notice.value = "Запись создана";
    } else if (activeRecord.value) {
      const updated = await lifecycleStore.update(entityType.value, activeRecord.value, payloadFromDraft());
      opened.value = updated;
      notice.value = "Изменения сохранены";
    }
    drawerMode.value = "view";
  } catch {
    formError.value = lifecycleStore.error.value;
  }
}

async function showHistory() {
  if (!activeRecord.value) return;
  historyOpen.value = true;
  historyLoading.value = true;
  try {
    historyRows.value = await lifecycleStore.history(entityType.value, activeRecord.value.id);
  } catch {
    historyRows.value = [];
  } finally {
    historyLoading.value = false;
  }
}

async function rowArchive(isArchived: boolean) {
  if (!activeRecord.value) return;
  await act(() => lifecycleStore.archive(entityType.value, activeRecord.value!, isArchived), isArchived ? "Запись архивирована" : "Запись возвращена");
}

async function rowDelete() {
  if (!activeRecord.value || !window.confirm(`Переместить «${entityTitle(activeRecord.value)}» в корзину? Запись можно восстановить.`)) return;
  await act(() => lifecycleStore.remove(entityType.value, activeRecord.value!), "Запись перемещена в корзину");
}

async function rowRestore() {
  if (!activeRecord.value) return;
  await act(() => lifecycleStore.restore(entityType.value, activeRecord.value!), "Запись восстановлена");
}

async function assignOwner() {
  if (!activeRecord.value || !ownerId.value || entityType.value === "notes") return;
  await act(() => lifecycleStore.reassign(entityType.value as Exclude<EntityType, "notes">, activeRecord.value!, ownerId.value), "Ответственный изменён", false);
}

async function qualifyLead(qualified: boolean) {
  if (!activeRecord.value) return;
  if (!qualified && !disqualificationReason.value.trim()) {
    formError.value = "Укажите причину дисквалификации.";
    return;
  }
  await act(() => lifecycleStore.qualify(activeRecord.value!, qualified, disqualificationReason.value.trim() || null), qualified ? "Лид квалифицирован" : "Лид дисквалифицирован", false);
  opened.value = records.value.find((item) => item.id === activeRecord.value?.id) ?? activeRecord.value;
}

async function convertLead() {
  if (!activeRecord.value || !conversion.stage_id) {
    formError.value = "Выберите этап сделки.";
    return;
  }
  await act(() => lifecycleStore.convert(activeRecord.value!, {
    stage_id: conversion.stage_id,
    title: conversion.title || null,
    amount: conversion.amount === "" ? null : Number(conversion.amount),
    ...(lifecycleStore.canReassign.value && conversion.owner_id ? { owner_id: conversion.owner_id } : {})
  }), "Лид конвертирован в сделку", false);
}

async function mergeSelected() {
  const target = activeRecord.value;
  if (!target || !["contacts", "leads", "deals"].includes(entityType.value)) return;
  const candidates = mergeSources.value.filter((item) => selectedIds.value.has(item.id));
  if (!candidates.length) {
    formError.value = "Отметьте записи той же компании в списке.";
    return;
  }
  if (!window.confirm(`Объединить ${candidates.length} записей с «${entityTitle(target)}»? Целевая запись сохранится, связи будут перенесены.`)) return;
  await act(() => lifecycleStore.merge(entityType.value as "contacts" | "leads" | "deals", target, candidates), "Записи объединены");
}

async function loadMergeCandidates() {
  const target = activeRecord.value;
  if (!target) return;
  lifecycleStore.clearSelected();
  await lifecycleStore.load({
    state: "active",
    filters: { company_id: target.company_id },
    search: "",
    page: 1,
    pageSize: 200
  });
  localSearch.value = "";
  opened.value = records.value.find((item) => item.id === target.id) ?? target;
}

async function applyBulk() {
  if (!lifecycleStore.selected.value.length) return;
  if (bulkAction.value === "delete" && !window.confirm(`Переместить ${lifecycleStore.selected.value.length} записей в корзину?`)) return;
  if (bulkAction.value === "reassign" && !ownerId.value) {
    formError.value = "Выберите или введите ID ответственного.";
    return;
  }
  await act(() => lifecycleStore.bulk(entityType.value, bulkAction.value, lifecycleStore.selected.value, bulkAction.value === "reassign" ? ownerId.value : undefined), "Массовая операция выполнена", false);
}

async function act(action: () => Promise<unknown>, success: string, close = true) {
  formError.value = "";
  try {
    await action();
    notice.value = success;
    if (close) closeDrawer();
  } catch {
    formError.value = lifecycleStore.error.value;
  }
}

function toggleAll() {
  if (isAllSelected.value) {
    lifecycleStore.clearSelected();
    return;
  }
  for (const record of records.value) if (!selectedIds.value.has(record.id) && mayEdit(record)) lifecycleStore.toggleSelected(record);
}

function recordOwner(record: LifecycleRecord) {
  if ("assigned_to_id" in record) return record.assigned_to_id;
  if ("owner_id" in record) return record.owner_id ?? null;
  return null;
}

function stateLabel(record: LifecycleRecord) {
  if (record.deleted_at) return "В корзине";
  if (record.is_archived) return "Архив";
  return "Активна";
}
</script>

<template>
  <section class="lifecycle-page stack">
    <section class="lifecycle-intro panel">
      <div>
        <p class="eyebrow">Frontend ↔ backend lifecycle</p>
        <h2>Управление CRM-записями</h2>
        <p>Редактирование, история, архив, корзина, ответственные и массовые операции в одном месте.</p>
      </div>
      <button v-if="lifecycleStore.canWrite.value" type="button" @click="openCreate"><UiIcon name="plus" :size="16" /> Создать {{ config.singular }}</button>
    </section>

    <nav class="entity-tabs" aria-label="Тип CRM-записей">
      <button v-for="type in ENTITY_TYPES" :key="type" type="button" :class="{ active: entityType === type }" @click="changeEntity(type)">{{ ENTITY_CONFIG[type].label }}</button>
    </nav>

    <section class="panel lifecycle-list-panel">
      <header class="lifecycle-controls">
        <div class="scope-tabs" role="tablist" aria-label="Состояние записей">
          <button type="button" :class="{ active: scope === 'active' }" @click="changeScope('active')">Активные</button>
          <button type="button" :class="{ active: scope === 'archived' }" @click="changeScope('archived')">Архив</button>
          <button v-if="lifecycleStore.canViewDeleted.value" type="button" :class="{ active: scope === 'deleted' }" @click="changeScope('deleted')">Корзина</button>
        </div>
        <div class="lifecycle-query">
          <label class="search-field"><span class="sr-only">Поиск</span><input v-model="localSearch" type="search" placeholder="Поиск на сервере…" /></label>
          <select v-if="['leads', 'deals', 'tasks'].includes(entityType)" aria-label="Фильтр статуса" @change="changeFilter('status_filter', ($event.target as HTMLSelectElement).value)">
            <option value="">Все статусы</option>
            <option value="new">Новые</option><option value="open">Открытые</option><option value="qualified">Квалифицированные</option><option value="done">Завершённые</option>
          </select>
          <select aria-label="Фильтр компании" @change="changeFilter('company_id', ($event.target as HTMLSelectElement).value)">
            <option value="">Все компании</option><option v-for="company in crmStore.companies.value" :key="company.id" :value="company.id">{{ company.name }}</option>
          </select>
          <select v-if="lifecycleStore.knownOwners.value.length" aria-label="Фильтр ответственного" @change="changeFilter(ownerFilterKey, ($event.target as HTMLSelectElement).value)">
            <option value="">Все ответственные</option><option v-for="member in lifecycleStore.knownOwners.value" :key="member.user_id" :value="member.user_id">{{ member.full_name }}</option>
          </select>
          <select v-if="entityType === 'tasks'" aria-label="Фильтр приоритета" @change="changeFilter('priority', ($event.target as HTMLSelectElement).value)"><option value="">Все приоритеты</option><option value="high">Высокий</option><option value="normal">Обычный</option><option value="low">Низкий</option></select>
          <select v-if="entityType === 'deals'" aria-label="Фильтр риска" @change="changeFilter('risk_level', ($event.target as HTMLSelectElement).value)"><option value="">Все риски</option><option value="high">Высокий</option><option value="medium">Средний</option><option value="low">Низкий</option></select>
          <select v-model="lifecycleStore.sort.value" aria-label="Сортировка" @change="changeSort">
            <option v-for="item in config.sortable" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
          <button class="secondary order-button" type="button" :aria-label="lifecycleStore.order.value === 'desc' ? 'По убыванию' : 'По возрастанию'" @click="lifecycleStore.order.value = lifecycleStore.order.value === 'desc' ? 'asc' : 'desc'; changeSort()"><UiIcon :name="lifecycleStore.order.value === 'desc' ? 'arrowDown' : 'arrowUp'" :size="16" /></button>
        </div>
      </header>

      <p v-if="lifecycleStore.error.value" class="alert error">{{ lifecycleStore.error.value }}</p>
      <p v-if="notice" class="alert success">{{ notice }}</p>

      <div class="table-scroll">
        <table class="data-table lifecycle-table">
          <thead><tr><th v-if="lifecycleStore.canWrite.value" class="check-cell"><input type="checkbox" :checked="isAllSelected" aria-label="Выбрать страницу" @change="toggleAll" /></th><th>Запись</th><th>Состояние</th><th>Версия</th><th>Изменена</th><th><span class="sr-only">Действия</span></th></tr></thead>
          <tbody>
            <tr v-for="record in records" :key="record.id" @click="openRecord(record)">
              <td v-if="lifecycleStore.canWrite.value" class="check-cell" @click.stop><input type="checkbox" :checked="selectedIds.has(record.id)" :disabled="!mayEdit(record)" :aria-label="`Выбрать ${entityTitle(record)}`" @change="lifecycleStore.toggleSelected(record)" /></td>
              <td><strong>{{ entityTitle(record) }}</strong><small>{{ entityMeta(record) || shortId(record.id) }}</small></td>
              <td><span class="state-chip" :class="scope">{{ stateLabel(record) }}</span></td>
              <td>v{{ record.version }}</td>
              <td>{{ formatValue("updated_at", record.updated_at || record.created_at) || "—" }}</td>
              <td><button class="secondary row-open" type="button" @click.stop="openRecord(record)">Открыть</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="lifecycleStore.loading.value" class="loading-state" aria-live="polite">Загрузка записей…</div>
      <div v-else-if="!records.length" class="empty-state"><strong>Записей нет</strong><span>Измените поиск или состояние списка.</span></div>

      <footer class="pagination-row">
        <span>{{ lifecycleStore.pagination.value.total }} записей · страница {{ lifecycleStore.pagination.value.page }} из {{ lifecycleStore.pagination.value.totalPages }}</span>
        <div><button class="secondary" type="button" :disabled="lifecycleStore.page.value <= 1" @click="lifecycleStore.load({ page: lifecycleStore.page.value - 1 })">← Назад</button><button class="secondary" type="button" :disabled="lifecycleStore.page.value >= lifecycleStore.pagination.value.totalPages" @click="lifecycleStore.load({ page: lifecycleStore.page.value + 1 })">Далее →</button></div>
      </footer>
    </section>

    <section v-if="lifecycleStore.selected.value.length" class="bulk-bar" aria-label="Массовые действия">
      <strong>Выбрано: {{ lifecycleStore.selected.value.length }}</strong>
      <select v-model="bulkAction"><option v-for="item in availableBulkActions" :key="item.value" :value="item.value">{{ item.label }}</option></select>
      <template v-if="bulkAction === 'reassign'">
        <select v-model="ownerId" aria-label="Ответственный"><option value="">Выберите ответственного</option><option v-for="member in lifecycleStore.knownOwners.value" :key="member.user_id" :value="member.user_id">{{ member.full_name }} · {{ member.role }}</option></select>
        <input v-model="ownerId" aria-label="UUID ответственного" placeholder="или UUID участника" />
      </template>
      <button type="button" @click="applyBulk">Применить</button>
      <button class="secondary" type="button" @click="lifecycleStore.clearSelected">Отменить выбор</button>
    </section>

    <div v-if="drawerMode" class="lifecycle-backdrop" @click.self="closeDrawer">
      <aside class="lifecycle-drawer" aria-modal="true" role="dialog" :aria-label="drawerMode === 'create' ? 'Создание записи' : entityTitle(activeRecord!)">
        <header>
          <div><p class="eyebrow">{{ config.label }} · {{ scope === "deleted" ? "корзина" : scope === "archived" ? "архив" : "активные" }}</p><h2>{{ drawerMode === "create" ? `Новый ${config.singular}` : entityTitle(activeRecord!) }}</h2></div>
          <button class="secondary close-button" type="button" aria-label="Закрыть" @click="closeDrawer"><UiIcon name="close" :size="19" /></button>
        </header>

        <form v-if="drawerMode === 'create' || drawerMode === 'edit'" class="lifecycle-form" @submit.prevent="saveRecord">
          <label v-for="field in formFields" :key="field.key">{{ field.label }}
            <textarea v-if="field.kind === 'textarea'" v-model="draft[field.key]" :required="field.required" rows="4"></textarea>
            <select v-else-if="field.kind === 'select' || field.kind === 'reference'" v-model="draft[field.key]" :required="field.required">
              <option value="">{{ field.required ? "Выберите" : "Не выбрано" }}</option>
              <option v-for="option in field.kind === 'reference' ? referenceOptions(field) : field.options" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
            <input v-else v-model="draft[field.key]" :type="field.kind || 'text'" :required="field.required" :min="field.min" :max="field.max" />
          </label>
          <p v-if="formError" class="alert error">{{ formError }}</p>
          <footer><button type="submit" :disabled="lifecycleStore.loading.value">{{ drawerMode === "create" ? "Создать" : "Сохранить" }}</button><button v-if="drawerMode === 'edit'" class="secondary" type="button" @click="drawerMode = 'view'">Отмена</button></footer>
        </form>

        <template v-else-if="activeRecord">
          <div class="record-summary"><span class="state-chip" :class="scope">{{ stateLabel(activeRecord) }}</span><span>Версия {{ activeRecord.version }}</span><span>ID {{ shortId(activeRecord.id) }}</span></div>
          <section class="record-actions">
            <button v-if="canMutateOpened && scope !== 'deleted'" class="secondary" type="button" @click="openEdit">Редактировать</button>
            <button class="secondary" type="button" @click="showHistory">История</button>
            <button v-if="canMutateOpened && scope === 'active'" class="secondary" type="button" @click="rowArchive(true)">Архивировать</button>
            <button v-if="canMutateOpened && scope === 'archived'" class="secondary" type="button" @click="rowArchive(false)">Вернуть из архива</button>
            <button v-if="canMutateOpened && scope !== 'deleted'" class="danger-button" type="button" @click="rowDelete">В корзину</button>
            <button v-if="canMutateOpened && scope === 'deleted'" type="button" @click="rowRestore">Восстановить</button>
          </section>

          <dl class="record-fields"><template v-for="field in config.fields" :key="field.key"><dt>{{ field.label }}</dt><dd>{{ formatValue(field.key, (activeRecord as unknown as Record<string, unknown>)[field.key]) || "—" }}</dd></template><dt>Ответственный</dt><dd>{{ shortId(recordOwner(activeRecord)) }}</dd></dl>

          <section v-if="canMutateOpened && lifecycleStore.canReassign.value && config.reassign" class="drawer-section lifecycle-tool">
            <h3>Ответственный</h3><p>Выберите участника. Если каталог недоступен менеджеру, вставьте UUID.</p>
            <select v-model="ownerId"><option value="">Выберите</option><option v-for="member in lifecycleStore.knownOwners.value" :key="member.user_id" :value="member.user_id">{{ member.full_name }} · {{ member.role }}</option></select>
            <input v-model="ownerId" placeholder="UUID участника" />
            <button type="button" @click="assignOwner">Назначить</button>
          </section>

          <section v-if="entityType === 'leads' && canMutateOpened && scope === 'active'" class="drawer-section lifecycle-tool">
            <h3>Квалификация лида</h3>
            <p>Текущий статус: <strong>{{ (activeRecord as Lead).status }}</strong></p>
            <div v-if="(activeRecord as Lead).status !== 'converted'" class="action-grid"><button type="button" @click="qualifyLead(true)">Квалифицировать</button><input v-model="disqualificationReason" placeholder="Причина отказа" /><button class="secondary" type="button" @click="qualifyLead(false)">Дисквалифицировать</button></div>
            <div v-if="(activeRecord as Lead).status === 'qualified'" class="conversion-form"><select v-model="conversion.stage_id" required><option value="">Этап сделки</option><option v-for="stage in crmStore.allStages.value" :key="stage.id" :value="stage.id">{{ stage.name }}</option></select><input v-model="conversion.title" placeholder="Название сделки" /><input v-model="conversion.amount" type="number" min="0" placeholder="Сумма" /><button type="button" @click="convertLead">Конвертировать в сделку</button></div>
            <RouterLink v-if="(activeRecord as Lead).converted_deal_id" class="secondary-link" :to="`/deals?deal=${(activeRecord as Lead).converted_deal_id}`">Открыть созданную сделку</RouterLink>
          </section>

          <section v-if="canMutateOpened && config.merge && scope === 'active'" class="drawer-section lifecycle-tool">
            <h3>Объединение</h3><p>Целевая запись сохранится. Связи отмеченных записей той же компании будут перенесены.</p>
            <button class="secondary" type="button" @click="loadMergeCandidates">Загрузить записи этой компании</button>
            <div class="merge-list"><label v-for="item in mergeSources" :key="item.id"><input type="checkbox" :checked="selectedIds.has(item.id)" @change="lifecycleStore.toggleSelected(item)" />{{ entityTitle(item) }}</label></div>
            <button type="button" :disabled="!mergeSources.some((item) => selectedIds.has(item.id))" @click="mergeSelected">Объединить выбранные</button>
          </section>

          <section v-if="historyOpen" class="drawer-section history-panel">
            <header><h3>История полей</h3><button class="secondary" type="button" @click="historyOpen = false">Скрыть</button></header>
            <p v-if="historyLoading">Загрузка…</p>
            <ol v-else-if="historyRows.length"><li v-for="change in historyRows" :key="change.id"><strong>{{ change.field_name }}</strong><span>{{ formatValue(change.field_name, change.old_value) || "—" }} → {{ formatValue(change.field_name, change.new_value) || "—" }}</span><small>v{{ change.entity_version }} · {{ shortId(change.changed_by_id) }} · {{ formatValue("created_at", change.created_at) }}</small></li></ol>
            <p v-else class="empty">Изменений пока нет.</p>
          </section>
          <p v-if="formError" class="alert error">{{ formError }}</p>
        </template>
      </aside>
    </div>

    <div v-if="lifecycleStore.conflict.value" class="conflict-backdrop" role="alertdialog" aria-modal="true" aria-label="Конфликт версии">
      <section class="conflict-card"><span class="conflict-icon"><UiIcon name="refresh" :size="22" /></span><h2>Запись уже изменена</h2><p>Серверная версия: {{ lifecycleStore.conflict.value.currentVersion ?? "неизвестна" }}. Автоматическая перезапись отключена, чтобы не потерять чужие изменения.</p><div><button type="button" @click="lifecycleStore.clearConflict(); lifecycleStore.load(); closeDrawer()">Загрузить актуальную версию</button><button class="secondary" type="button" @click="lifecycleStore.clearConflict">Отмена</button></div></section>
    </div>
  </section>
</template>

<style scoped>
.lifecycle-page { padding-bottom: 84px; }
.lifecycle-intro { display: flex; align-items: center; justify-content: space-between; gap: 24px; }
.lifecycle-intro h2 { margin: 3px 0 7px; font-size: 24px; }
.lifecycle-intro p:last-child { margin: 0; color: var(--muted); }
.entity-tabs, .scope-tabs { display: flex; gap: 4px; overflow-x: auto; padding: 4px; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); }
.entity-tabs { width: fit-content; max-width: 100%; }
.entity-tabs button, .scope-tabs button { min-height: 34px; color: var(--muted); background: transparent; white-space: nowrap; }
.entity-tabs button.active, .scope-tabs button.active { color: var(--text); background: var(--surface-solid); box-shadow: 0 1px 5px rgb(0 0 0 / 10%); }
.lifecycle-list-panel { padding: 0; overflow: hidden; }
.lifecycle-controls { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 16px; border-bottom: 1px solid var(--line-soft); }
.lifecycle-query { display: flex; gap: 8px; min-width: 0; }
.lifecycle-query input { min-width: min(260px, 30vw); }
.lifecycle-query select { width: auto; min-width: 145px; }
.order-button { width: 40px; padding: 0; font-size: 18px; }
.table-scroll { overflow-x: auto; }
.lifecycle-table { min-width: 760px; }
.lifecycle-table td strong, .lifecycle-table td small { display: block; }
.lifecycle-table td small { max-width: 460px; margin-top: 4px; overflow: hidden; color: var(--muted); text-overflow: ellipsis; white-space: nowrap; }
.lifecycle-table .check-cell { width: 42px; text-align: center; }
.lifecycle-table .row-open { min-height: 32px; padding: 0 10px; }
.state-chip { display: inline-flex; border-radius: 999px; padding: 5px 8px; color: #17663a; background: #e9f8ef; font-size: 11px; font-weight: 700; }
.state-chip.archived { color: #7a5712; background: #fff3d6; }
.state-chip.deleted { color: #a02929; background: #fdecec; }
.loading-state, .empty-state { display: grid; place-items: center; gap: 5px; min-height: 180px; color: var(--muted); }
.empty-state strong { color: var(--text); }
.pagination-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 16px; border-top: 1px solid var(--line-soft); color: var(--muted); font-size: 13px; }
.pagination-row > div { display: flex; gap: 8px; }
.bulk-bar { position: fixed; z-index: 16; right: 24px; bottom: 20px; left: max(24px, calc(252px + 24px)); display: flex; align-items: center; gap: 10px; border: 1px solid #bed7f5; border-radius: 12px; padding: 12px 14px; background: #f4f9ff; box-shadow: 0 14px 40px rgb(27 64 112 / 18%); }
.bulk-bar select, .bulk-bar input { width: auto; min-width: 190px; }
.lifecycle-backdrop, .conflict-backdrop { position: fixed; inset: 0; z-index: 90; background: rgb(15 23 42 / 32%); backdrop-filter: blur(2px); }
.lifecycle-drawer { position: absolute; top: 0; right: 0; width: min(560px, 100%); height: 100%; overflow-y: auto; padding: 24px; background: #fff; box-shadow: -20px 0 50px rgb(15 23 42 / 16%); }
.lifecycle-drawer > header, .history-panel > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.lifecycle-drawer h2 { margin: 3px 0 0; font-size: 24px; overflow-wrap: anywhere; }
.close-button { width: 38px; padding: 0; font-size: 24px; }
.lifecycle-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 24px; }
.lifecycle-form label { margin: 0; }
.lifecycle-form label:has(textarea), .lifecycle-form .alert, .lifecycle-form footer { grid-column: 1 / -1; }
.lifecycle-form footer, .record-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.record-summary { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin: 20px 0; color: var(--muted); font-size: 13px; }
.record-actions { padding-bottom: 18px; border-bottom: 1px solid var(--line-soft); }
.danger-button { color: #a02929; border-color: #efc2c2; background: #fff6f6; }
.record-fields { display: grid; grid-template-columns: 150px minmax(0, 1fr); gap: 0; margin: 18px 0; }
.record-fields dt, .record-fields dd { margin: 0; border-bottom: 1px solid var(--line-soft); padding: 10px 0; }
.record-fields dt { color: var(--muted); }
.record-fields dd { overflow-wrap: anywhere; }
.lifecycle-tool { display: grid; gap: 10px; }
.lifecycle-tool h3, .lifecycle-tool p { margin: 0; }
.lifecycle-tool p { color: var(--muted); font-size: 13px; }
.action-grid, .conversion-form { display: grid; gap: 8px; }
.merge-list { display: grid; gap: 7px; max-height: 170px; overflow-y: auto; }
.merge-list label { display: flex; align-items: center; gap: 9px; margin: 0; }
.history-panel ol { display: grid; gap: 10px; margin: 12px 0 0; padding: 0; list-style: none; }
.history-panel li { display: grid; gap: 4px; border: 1px solid var(--line); border-radius: 8px; padding: 11px; }
.history-panel small { color: var(--muted); }
.conflict-backdrop { display: grid; place-items: center; padding: 20px; z-index: 110; }
.conflict-card { width: min(440px, 100%); border-radius: 14px; padding: 28px; background: #fff; box-shadow: 0 24px 70px rgb(15 23 42 / 24%); text-align: center; }
.conflict-icon { display: grid; place-items: center; width: 48px; height: 48px; margin: 0 auto; border-radius: 50%; color: #8a5b00; background: #fff1cf; font-size: 24px; }
.conflict-card h2 { margin: 14px 0 8px; }
.conflict-card p { color: var(--muted); }
.conflict-card > div { display: flex; justify-content: center; gap: 8px; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
@media (max-width: 920px) { .bulk-bar { left: 14px; right: 14px; overflow-x: auto; } .lifecycle-controls { align-items: stretch; flex-direction: column; } .lifecycle-query { flex-wrap: wrap; } .lifecycle-query input { min-width: 200px; } }
@media (max-width: 620px) { .lifecycle-intro { align-items: stretch; flex-direction: column; } .entity-tabs { width: 100%; } .lifecycle-query > * { flex: 1 1 140px; } .pagination-row { align-items: stretch; flex-direction: column; } .pagination-row > div button { flex: 1; } .lifecycle-form { grid-template-columns: 1fr; } .record-fields { grid-template-columns: 110px minmax(0, 1fr); } .bulk-bar { flex-wrap: wrap; } .bulk-bar strong { flex: 1 0 100%; } }
</style>
