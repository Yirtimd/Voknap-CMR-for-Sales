import { computed, ref } from "vue";

import { ApiError, api, apiPage, buildQuery, post, type QueryParams, type QueryValue } from "../api";
import { crmStore } from "./crm";
import type {
  BulkAction,
  BulkActionResult,
  Deal,
  EntityType,
  EntityVersion,
  FieldChange,
  Lead,
  LeadConversionRequest,
  LeadConversionResponse,
  LifecycleResult,
  MergeResult,
  Note,
  Pagination,
  Task,
  Contact
} from "../types";

export type LifecycleRecord = Contact | Lead | Deal | Task | Note;
export type LifecycleState = "active" | "archived" | "deleted";
export type LifecycleFilters = Record<string, QueryValue | QueryValue[]>;

export type LifecycleQuery = {
  entityType?: EntityType;
  state?: LifecycleState;
  search?: string;
  filters?: LifecycleFilters;
  sort?: string;
  order?: "asc" | "desc";
  page?: number;
  pageSize?: number;
};

export type LifecycleConflict = {
  entityType: EntityType;
  entityId: string;
  currentVersion: number | null;
  detail: unknown;
};

export type LifecycleMember = {
  id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  created_at?: string;
};

const entityType = ref<EntityType>("contacts");
const state = ref<LifecycleState>("active");
const search = ref("");
const filters = ref<LifecycleFilters>({});
const sort = ref("created_at");
const order = ref<"asc" | "desc">("desc");
const page = ref(1);
const pageSize = ref(25);
const records = ref<LifecycleRecord[]>([]);
const pagination = ref<Pagination>({ page: 1, pageSize: 25, total: 0, totalPages: 1 });
const selected = ref<EntityVersion[]>([]);
const loading = ref(false);
const error = ref("");
const conflict = ref<LifecycleConflict | null>(null);
const members = ref<LifecycleMember[]>([]);

let listController: AbortController | null = null;

const permissions = computed(() => new Set(crmStore.me.value?.permissions ?? []));
const role = computed(() => crmStore.me.value?.role);
const canRead = computed(() => permissions.value.has("crm:read") || Boolean(role.value));
const canWrite = computed(() => permissions.value.has("crm:write") || ["owner", "admin", "sales_manager", "sales_rep"].includes(role.value ?? ""));
const canReassign = computed(() => permissions.value.has("assignments:manage") || ["owner", "admin", "sales_manager"].includes(role.value ?? ""));
const canManageMembers = computed(() => permissions.value.has("members:manage") || ["owner", "admin"].includes(role.value ?? ""));
const canViewDeleted = computed(() => permissions.value.has("sales:manage") || ["owner", "admin", "sales_manager"].includes(role.value ?? ""));
const canMerge = computed(() => canWrite.value);

const knownOwners = computed<LifecycleMember[]>(() => {
  const byUserId = new Map<string, LifecycleMember>();
  for (const member of members.value) byUserId.set(member.user_id, member);
  const me = crmStore.me.value;
  if (me && !byUserId.has(me.user_id)) {
    byUserId.set(me.user_id, {
      id: me.user_id,
      user_id: me.user_id,
      email: me.email,
      full_name: me.full_name,
      role: me.role
    });
  }
  for (const record of records.value) {
    const userId = recordOwnerId(record);
    if (userId && !byUserId.has(userId)) {
      byUserId.set(userId, { id: userId, user_id: userId, email: userId, full_name: userId, role: "member" });
    }
  }
  return [...byUserId.values()];
});

function setQuery(next: LifecycleQuery = {}) {
  if (next.entityType) entityType.value = next.entityType;
  if (next.state) state.value = next.state;
  if (next.search !== undefined) search.value = next.search;
  if (next.filters !== undefined) filters.value = next.filters;
  if (next.sort) sort.value = next.sort;
  if (next.order) order.value = next.order;
  if (next.page) page.value = Math.max(1, next.page);
  if (next.pageSize) pageSize.value = Math.min(200, Math.max(1, next.pageSize));
}

async function load(next: LifecycleQuery = {}) {
  setQuery(next);
  listController?.abort();
  const controller = new AbortController();
  listController = controller;
  loading.value = true;
  error.value = "";
  try {
    const query = currentQuery();
    if (state.value === "active") {
      const result = await apiPage<LifecycleRecord>(
        buildQuery(`/sales/${entityType.value}`, listParams(query)),
        { signal: controller.signal },
        crmStore.token.value,
        crmStore.tenantId.value,
        { page: page.value, pageSize: pageSize.value }
      );
      if (controller.signal.aborted) return;
      records.value = result.items;
      pagination.value = result.pagination;
    } else {
      const all = await loadNonActiveRecords(query, controller.signal);
      if (controller.signal.aborted) return;
      const matching = all.filter((record) => matchesState(record, state.value));
      const total = matching.length;
      const pages = Math.max(1, Math.ceil(total / pageSize.value));
      if (page.value > pages) page.value = pages;
      const start = (page.value - 1) * pageSize.value;
      records.value = matching.slice(start, start + pageSize.value);
      pagination.value = { page: page.value, pageSize: pageSize.value, total, totalPages: pages };
    }
    pruneSelected();
  } catch (caught) {
    if (isAborted(caught)) return;
    error.value = messageOf(caught);
  } finally {
    if (listController === controller) loading.value = false;
  }
}

async function create(type: EntityType, payload: Record<string, unknown>) {
  return mutation(type, undefined, async () => {
    const record = await api<LifecycleRecord>(
      `/sales/${type}`,
      post(payload),
      crmStore.token.value,
      crmStore.tenantId.value
    );
    syncCrmRecord(type, record);
    return record;
  });
}

async function update(type: EntityType, entity: EntityVersion, payload: Record<string, unknown>) {
  return mutation(type, entity.id, async () => {
    const record = await api<LifecycleRecord>(
      `/sales/${type}/${entity.id}`,
      post({ ...payload, version: entity.version }, "PATCH"),
      crmStore.token.value,
      crmStore.tenantId.value
    );
    syncCrmRecord(type, record);
    return record;
  });
}

async function archive(type: EntityType, entity: EntityVersion, isArchived = true) {
  return mutation(type, entity.id, async () => {
    const result = await api<LifecycleResult>(
      `/sales/${type}/${entity.id}/archive`,
      post({ version: entity.version, is_archived: isArchived }, "PATCH"),
      crmStore.token.value,
      crmStore.tenantId.value
    );
    patchLifecycleRecord(entity.id, result);
    await syncCrmLists();
    return result;
  });
}

async function remove(type: EntityType, entity: EntityVersion) {
  return mutation(type, entity.id, async () => {
    const result = await api<LifecycleResult>(
      buildQuery(`/sales/${type}/${entity.id}`, { version: entity.version }),
      { method: "DELETE" },
      crmStore.token.value,
      crmStore.tenantId.value
    );
    patchLifecycleRecord(entity.id, result);
    await syncCrmLists();
    return result;
  });
}

async function restore(type: EntityType, entity: EntityVersion) {
  return mutation(type, entity.id, async () => {
    const result = await api<LifecycleResult>(
      `/sales/${type}/${entity.id}/restore`,
      post({ version: entity.version }),
      crmStore.token.value,
      crmStore.tenantId.value
    );
    patchLifecycleRecord(entity.id, result);
    await syncCrmLists();
    return result;
  });
}

async function reassign(type: Exclude<EntityType, "notes">, entity: EntityVersion, ownerId: string) {
  return mutation(type, entity.id, async () => {
    const result = await api<LifecycleResult>(
      `/sales/${type}/${entity.id}/owner`,
      post({ version: entity.version, owner_id: ownerId }, "PATCH"),
      crmStore.token.value,
      crmStore.tenantId.value
    );
    patchLifecycleRecord(entity.id, result);
    await syncCrmLists();
    return result;
  });
}

async function history(type: EntityType, id: string) {
  return mutation(type, id, () =>
    api<FieldChange[]>(`/sales/${type}/${id}/history`, {}, crmStore.token.value, crmStore.tenantId.value), false
  );
}

async function bulk(type: EntityType, action: BulkAction, items = selected.value, ownerId?: string | null) {
  if (items.length === 0) return null;
  return mutation(type, undefined, async () => {
    const result = await api<BulkActionResult>(
      `/sales/${type}/bulk`,
      post({ action, items, ...(ownerId !== undefined ? { owner_id: ownerId } : {}) }),
      crmStore.token.value,
      crmStore.tenantId.value
    );
    selected.value = [];
    await syncCrmLists();
    return result;
  });
}

async function merge(type: Extract<EntityType, "contacts" | "leads" | "deals">, target: EntityVersion, sources: EntityVersion[]) {
  return mutation(type, target.id, async () => {
    const result = await api<MergeResult>(
      `/sales/${type}/${target.id}/merge`,
      post({ target_version: target.version, sources }),
      crmStore.token.value,
      crmStore.tenantId.value
    );
    selected.value = [];
    await syncCrmLists();
    return result;
  });
}

async function qualify(entity: EntityVersion, qualified: boolean, reason?: string | null) {
  return mutation("leads", entity.id, async () => {
    const result = await api<Lead>(
      `/sales/leads/${entity.id}/qualify`,
      post({ version: entity.version, qualified, ...(reason ? { reason } : {}) }),
      crmStore.token.value,
      crmStore.tenantId.value
    );
    syncCrmRecord("leads", result);
    return result;
  });
}

async function convert(entity: EntityVersion, payload: Omit<LeadConversionRequest, "version">) {
  return mutation("leads", entity.id, async () => {
    const result = await api<LeadConversionResponse>(
      `/sales/leads/${entity.id}/convert`,
      post({ ...payload, version: entity.version }),
      crmStore.token.value,
      crmStore.tenantId.value
    );
    syncCrmRecord("leads", result.lead);
    syncCrmRecord("deals", result.deal);
    return result;
  });
}

async function loadMembers() {
  if (!canManageMembers.value) return knownOwners.value;
  try {
    members.value = await api<LifecycleMember[]>("/accounts/members", {}, crmStore.token.value, crmStore.tenantId.value);
  } catch (caught) {
    // A revoked role must not block the editor: it can still show the current owner.
    if (!(caught instanceof ApiError) || caught.status !== 403) error.value = messageOf(caught);
  }
  return knownOwners.value;
}

function toggleSelected(record: EntityVersion) {
  const index = selected.value.findIndex((item) => item.id === record.id);
  if (index === -1) selected.value = [...selected.value, { id: record.id, version: record.version }];
  else selected.value = selected.value.filter((item) => item.id !== record.id);
}

function clearSelected() {
  selected.value = [];
}

function clearConflict() {
  conflict.value = null;
}

function currentQuery(): Required<Pick<LifecycleQuery, "entityType" | "state" | "search" | "filters" | "sort" | "order" | "page" | "pageSize">> {
  return {
    entityType: entityType.value,
    state: state.value,
    search: search.value,
    filters: filters.value,
    sort: sort.value,
    order: order.value,
    page: page.value,
    pageSize: pageSize.value
  };
}

function listParams(query: ReturnType<typeof currentQuery>, overrides: QueryParams = {}): QueryParams {
  return {
    search: query.search || undefined,
    ...query.filters,
    sort: query.sort,
    order: query.order,
    page: query.page,
    page_size: query.pageSize,
    ...overrides
  };
}

async function loadNonActiveRecords(query: ReturnType<typeof currentQuery>, signal: AbortSignal) {
  const all: LifecycleRecord[] = [];
  let serverPage = 1;
  let more = true;
  while (more && !signal.aborted) {
    const result = await apiPage<LifecycleRecord>(
      buildQuery(`/sales/${query.entityType}`, listParams(query, {
        include_archived: true,
        include_deleted: query.state === "deleted",
        page: serverPage,
        page_size: 200
      })),
      { signal },
      crmStore.token.value,
      crmStore.tenantId.value,
      { page: serverPage, pageSize: 200 }
    );
    all.push(...result.items);
    // Headers may be hidden by an unchanged CORS policy. A short page is then
    // the reliable termination condition; with headers it avoids needless reads.
    more = result.items.length === 200 && (serverPage < result.pagination.totalPages || result.pagination.totalPages <= serverPage);
    serverPage += 1;
  }
  return all;
}

async function mutation<T>(type: EntityType, id: string | undefined, action: () => Promise<T>, reload = true): Promise<T> {
  error.value = "";
  conflict.value = null;
  loading.value = true;
  try {
    const result = await action();
    if (reload) await load();
    return result;
  } catch (caught) {
    if (caught instanceof ApiError && caught.status === 409) {
      conflict.value = { entityType: type, entityId: id ?? "", currentVersion: caught.currentVersion, detail: caught.detail };
    }
    error.value = messageOf(caught);
    throw caught;
  } finally {
    loading.value = false;
  }
}

function matchesState(record: LifecycleRecord, value: LifecycleState) {
  if (value === "deleted") return record.deleted_at !== null;
  if (value === "archived") return record.deleted_at === null && record.is_archived;
  return record.deleted_at === null && !record.is_archived;
}

function patchLifecycleRecord(id: string, result: LifecycleResult) {
  records.value = records.value.map((record) =>
    record.id === id
      ? { ...record, version: result.version, is_archived: result.is_archived, deleted_at: result.deleted_at }
      : record
  ) as LifecycleRecord[];
  selected.value = selected.value.map((item) => item.id === id ? { id, version: result.version } : item);
}

function syncCrmRecord(type: EntityType, record: LifecycleRecord) {
  const target = crmList(type);
  const index = target.value.findIndex((item) => item.id === record.id);
  if (record.deleted_at || record.is_archived) {
    if (index >= 0) target.value.splice(index, 1);
    return;
  }
  if (index >= 0) target.value.splice(index, 1, record as never);
  else target.value.unshift(record as never);
}

async function syncCrmLists() {
  if (crmStore.isAuthed.value) await crmStore.refreshAll();
}

function crmList(type: EntityType) {
  switch (type) {
    case "contacts": return crmStore.contacts;
    case "leads": return crmStore.leads;
    case "deals": return crmStore.deals;
    case "tasks": return crmStore.tasks;
    case "notes": return crmStore.notes;
  }
}

function recordOwnerId(record: LifecycleRecord) {
  if ("assigned_to_id" in record) return record.assigned_to_id;
  if ("owner_id" in record) return record.owner_id ?? null;
  return null;
}

function pruneSelected() {
  const versions = new Map(records.value.map((record) => [record.id, record.version]));
  selected.value = selected.value
    .filter((item) => !versions.has(item.id) || versions.get(item.id) === item.version);
}

function isAborted(caught: unknown) {
  return caught instanceof DOMException && caught.name === "AbortError";
}

function messageOf(caught: unknown) {
  return caught instanceof Error ? caught.message : "Не удалось выполнить действие";
}

export const lifecycleStore = {
  entityType,
  state,
  search,
  filters,
  sort,
  order,
  page,
  pageSize,
  records,
  pagination,
  selected,
  loading,
  error,
  conflict,
  members,
  knownOwners,
  canRead,
  canWrite,
  canReassign,
  canManageMembers,
  canViewDeleted,
  canMerge,
  setQuery,
  currentQuery,
  load,
  create,
  update,
  archive,
  remove,
  restore,
  reassign,
  history,
  bulk,
  merge,
  qualify,
  convert,
  loadMembers,
  toggleSelected,
  clearSelected,
  clearConflict
};
