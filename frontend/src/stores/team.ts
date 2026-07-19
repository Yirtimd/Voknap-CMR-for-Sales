import { computed, ref } from "vue";

import { ApiError, api, post } from "../api";
import type {
  AssignmentRule,
  InvitationAcceptResponse,
  Lead,
  LeadQueue,
  Membership,
  MembershipRole,
  SalesTeam,
  TeamInvitation,
  Territory
} from "../types";
import { crmStore } from "./crm";

const members = ref<Membership[]>([]);
const invitations = ref<TeamInvitation[]>([]);
const teams = ref<SalesTeam[]>([]);
const queues = ref<LeadQueue[]>([]);
const territories = ref<Territory[]>([]);
const assignmentRules = ref<AssignmentRule[]>([]);
const invitationLinks = ref<Record<string, string>>({});
const loading = ref(false);
const error = ref("");
const success = ref("");

const permissions = computed(() => new Set(crmStore.me.value?.permissions ?? []));
const role = computed(() => crmStore.me.value?.role);
const canManageMembers = computed(() =>
  permissions.value.has("members:manage") || role.value === "owner" || role.value === "admin"
);
const canManageAssignments = computed(() =>
  permissions.value.has("assignments:manage") || ["owner", "admin", "sales_manager"].includes(role.value ?? "")
);
const canClaimLead = computed(() =>
  permissions.value.has("crm:write") || ["owner", "admin", "sales_manager", "sales_rep"].includes(role.value ?? "")
);
const canOpen = computed(() => canManageMembers.value || canManageAssignments.value);
const activeMembers = computed(() => members.value.filter((member) => member.is_active));

function auth() {
  return [crmStore.token.value, crmStore.tenantId.value] as const;
}

async function refreshMembers() {
  if (!canManageMembers.value) {
    members.value = [];
    return;
  }
  members.value = await api<Membership[]>("/accounts/members", {}, ...auth());
}

async function refreshInvitations() {
  if (!canManageMembers.value) {
    invitations.value = [];
    return;
  }
  invitations.value = await api<TeamInvitation[]>("/accounts/invitations", {}, ...auth());
}

async function refreshTeams() {
  if (!canManageAssignments.value) {
    teams.value = [];
    return;
  }
  teams.value = await api<SalesTeam[]>("/accounts/teams", {}, ...auth());
}

async function refreshQueues() {
  if (!canManageAssignments.value) {
    queues.value = [];
    return;
  }
  queues.value = await api<LeadQueue[]>("/accounts/queues", {}, ...auth());
}

async function refreshTerritories() {
  if (!canManageAssignments.value) {
    territories.value = [];
    return;
  }
  territories.value = await api<Territory[]>("/accounts/territories", {}, ...auth());
}

async function refreshAssignmentRules() {
  if (!canManageAssignments.value) {
    assignmentRules.value = [];
    return;
  }
  assignmentRules.value = await api<AssignmentRule[]>("/accounts/assignment-rules", {}, ...auth());
}

async function refreshAll() {
  loading.value = true;
  error.value = "";
  try {
    await Promise.all([
      refreshMembers(),
      refreshInvitations(),
      refreshTeams(),
      refreshQueues(),
      refreshTerritories(),
      refreshAssignmentRules()
    ]);
  } catch (caught) {
    error.value = errorMessage(caught);
  } finally {
    loading.value = false;
  }
}

async function createInvitation(payload: {
  email: string;
  role: MembershipRole;
  team_id?: string | null;
  manager_membership_id?: string | null;
  expires_in_hours: number;
}) {
  return mutate(async () => {
    const invitation = await api<TeamInvitation>("/accounts/invitations", post(payload), ...auth());
    if (invitation.token) {
      invitationLinks.value = {
        ...invitationLinks.value,
        [invitation.id]: `${window.location.origin}/accept-invitation?token=${encodeURIComponent(invitation.token)}`
      };
    }
    await refreshInvitations();
    return invitation;
  }, "Приглашение создано. Скопируйте ссылку сейчас.");
}

async function revokeInvitation(id: string) {
  return mutate(async () => {
    await api<void>(`/accounts/invitations/${id}`, { method: "DELETE" }, ...auth());
    await refreshInvitations();
  }, "Приглашение отозвано");
}

async function updateMemberRole(id: string, role: MembershipRole) {
  return mutate(async () => {
    const result = await api<Membership>(`/accounts/members/${id}`, post({ role }, "PATCH"), ...auth());
    await refreshMembers();
    return result;
  }, "Роль обновлена");
}

async function updateMemberStructure(id: string, teamId: string | null, managerId: string | null) {
  return mutate(async () => {
    const result = await api<Membership>(
      `/accounts/members/${id}/structure`,
      post({ team_id: teamId, manager_membership_id: managerId }, "PATCH"),
      ...auth()
    );
    await Promise.all([refreshMembers(), refreshTeams()]);
    return result;
  }, "Структура обновлена");
}

async function updateMemberStatus(id: string, isActive: boolean, reassignToUserId?: string | null) {
  return mutate(async () => {
    const result = await api<Membership>(
      `/accounts/members/${id}/status`,
      post({ is_active: isActive, reassign_to_user_id: reassignToUserId ?? null }, "PATCH"),
      ...auth()
    );
    await refreshMembers();
    return result;
  }, isActive ? "Участник активирован" : "Участник деактивирован, объекты переназначены");
}

async function createTeam(payload: { name: string; manager_membership_id?: string | null }) {
  return mutate(async () => {
    const result = await api<SalesTeam>("/accounts/teams", post(payload), ...auth());
    await refreshTeams();
    return result;
  }, "Команда создана");
}

async function updateTeam(id: string, payload: Partial<Pick<SalesTeam, "name" | "manager_membership_id" | "is_active">>) {
  return mutate(async () => {
    const result = await api<SalesTeam>(`/accounts/teams/${id}`, post(payload, "PATCH"), ...auth());
    await refreshTeams();
    return result;
  }, "Команда обновлена");
}

async function createQueue(payload: { name: string; team_id?: string | null; strategy: "manual" | "round_robin"; membership_ids: string[] }) {
  return mutate(async () => {
    const result = await api<LeadQueue>("/accounts/queues", post(payload), ...auth());
    await refreshQueues();
    return result;
  }, "Очередь создана");
}

async function updateQueue(id: string, payload: Partial<Pick<LeadQueue, "name" | "team_id" | "strategy" | "membership_ids" | "is_active">>) {
  return mutate(async () => {
    const result = await api<LeadQueue>(`/accounts/queues/${id}`, post(payload, "PATCH"), ...auth());
    await refreshQueues();
    return result;
  }, "Очередь обновлена");
}

async function claimLead(queueId: string) {
  return mutate(async () => {
    const lead = await api<Lead>(`/accounts/queues/${queueId}/claim`, post({}), ...auth());
    const index = crmStore.leads.value.findIndex((item) => item.id === lead.id);
    if (index >= 0) crmStore.leads.value.splice(index, 1, lead);
    else crmStore.leads.value.unshift(lead);
    return lead;
  }, "Лид назначен вам");
}

async function createTerritory(payload: {
  name: string;
  country_code?: string | null;
  region?: string | null;
  industry?: string | null;
  owner_membership_id?: string | null;
  team_id?: string | null;
  priority: number;
}) {
  return mutate(async () => {
    const result = await api<Territory>("/accounts/territories", post(payload), ...auth());
    await refreshTerritories();
    return result;
  }, "Территория создана");
}

async function updateTerritory(id: string, payload: Partial<Omit<Territory, "id" | "created_at">>) {
  return mutate(async () => {
    const result = await api<Territory>(`/accounts/territories/${id}`, post(payload, "PATCH"), ...auth());
    await refreshTerritories();
    return result;
  }, "Территория обновлена");
}

async function createAssignmentRule(payload: {
  name: string;
  entity_type: "lead" | "company";
  criteria: Record<string, string>;
  target_type: "member" | "team" | "queue" | "territory";
  target_id: string;
  priority: number;
}) {
  return mutate(async () => {
    const result = await api<AssignmentRule>("/accounts/assignment-rules", post(payload), ...auth());
    await refreshAssignmentRules();
    return result;
  }, "Правило создано");
}

async function updateAssignmentRule(id: string, payload: Partial<Omit<AssignmentRule, "id" | "created_at" | "entity_type">>) {
  return mutate(async () => {
    const result = await api<AssignmentRule>(`/accounts/assignment-rules/${id}`, post(payload, "PATCH"), ...auth());
    await refreshAssignmentRules();
    return result;
  }, "Правило обновлено");
}

async function acceptInvitation(payload: { token: string; full_name?: string | null; password: string }) {
  return mutate(
    () => api<InvitationAcceptResponse>("/auth/invitations/accept", post(payload)),
    "Приглашение принято"
  );
}

async function mutate<T>(action: () => Promise<T>, message: string): Promise<T> {
  loading.value = true;
  error.value = "";
  success.value = "";
  try {
    const result = await action();
    success.value = message;
    return result;
  } catch (caught) {
    error.value = errorMessage(caught);
    throw caught;
  } finally {
    loading.value = false;
  }
}

function errorMessage(caught: unknown) {
  if (!(caught instanceof ApiError)) return caught instanceof Error ? caught.message : "Неизвестная ошибка";
  const detail = typeof caught.detail === "string"
    ? caught.detail
    : caught.detail && typeof caught.detail === "object" && "message" in caught.detail
      ? String(caught.detail.message)
      : caught.message;
  const labels: Record<number, string> = {
    403: "Недостаточно прав",
    404: "Объект не найден",
    409: "Конфликт данных",
    422: "Проверьте заполнение полей"
  };
  return `${labels[caught.status] ?? `HTTP ${caught.status}`}: ${detail}`;
}

function clearMessages() {
  error.value = "";
  success.value = "";
}

export const teamStore = {
  members,
  invitations,
  teams,
  queues,
  territories,
  assignmentRules,
  invitationLinks,
  loading,
  error,
  success,
  canManageMembers,
  canManageAssignments,
  canClaimLead,
  canOpen,
  activeMembers,
  refreshMembers,
  refreshInvitations,
  refreshTeams,
  refreshQueues,
  refreshTerritories,
  refreshAssignmentRules,
  refreshAll,
  createInvitation,
  revokeInvitation,
  updateMemberRole,
  updateMemberStructure,
  updateMemberStatus,
  createTeam,
  updateTeam,
  createQueue,
  updateQueue,
  claimLead,
  createTerritory,
  updateTerritory,
  createAssignmentRule,
  updateAssignmentRule,
  acceptInvitation,
  clearMessages
};
