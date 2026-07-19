<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import { crmStore } from "../stores/crm";
import { teamStore } from "../stores/team";
import type { AssignmentTargetType, Membership, MembershipRole, TeamInvitation } from "../types";

type Tab = "members" | "invitations" | "teams" | "queues" | "territories" | "rules";

const activeTab = ref<Tab>("members");
const tabs: Array<{ id: Tab; label: string; permission: "members" | "assignments" }> = [
  { id: "members", label: "Участники", permission: "members" },
  { id: "invitations", label: "Приглашения", permission: "members" },
  { id: "teams", label: "Команды", permission: "assignments" },
  { id: "queues", label: "Очереди лидов", permission: "assignments" },
  { id: "territories", label: "Территории", permission: "assignments" },
  { id: "rules", label: "Правила назначения", permission: "assignments" }
];
const roles: Array<{ value: MembershipRole; label: string }> = [
  { value: "owner", label: "Владелец" },
  { value: "admin", label: "Администратор" },
  { value: "sales_manager", label: "Руководитель продаж" },
  { value: "sales_rep", label: "Менеджер" },
  { value: "viewer", label: "Наблюдатель" }
];

const memberDrafts = reactive<Record<string, { role: MembershipRole; team_id: string; manager_membership_id: string }>>({});
const teamManagerDrafts = reactive<Record<string, string>>({});
const queueDrafts = reactive<Record<string, { team_id: string; strategy: "manual" | "round_robin"; membership_ids: string[] }>>({});
const invitationForm = reactive({ email: "", role: "sales_rep" as MembershipRole, team_id: "", manager_membership_id: "", expires_in_hours: 72 });
const teamForm = reactive({ name: "", manager_membership_id: "" });
const queueForm = reactive({ name: "", team_id: "", strategy: "round_robin" as "manual" | "round_robin", membership_ids: [] as string[] });
const territoryForm = reactive({ name: "", country_code: "", region: "", industry: "", target_type: "member" as "member" | "team", target_id: "", priority: 100 });
const ruleForm = reactive({ name: "", entity_type: "lead" as "lead" | "company", criteria: '{"source":"website"}', target_type: "queue" as AssignmentTargetType, target_id: "", priority: 100 });
const deactivationTarget = ref<Membership | null>(null);
const replacementUserId = ref("");
const localError = ref("");
const profileError = ref("");

const visibleTabs = computed(() => tabs.filter((tab) => tab.permission === "members" ? teamStore.canManageMembers.value : teamStore.canManageAssignments.value));
const replacementMembers = computed(() => teamStore.activeMembers.value.filter((member) => member.id !== deactivationTarget.value?.id));
const ruleTargets = computed(() => {
  if (ruleForm.target_type === "member") return teamStore.activeMembers.value.map((item) => ({ id: item.id, label: item.full_name }));
  if (ruleForm.target_type === "team") return teamStore.teams.value.filter((item) => item.is_active).map((item) => ({ id: item.id, label: item.name }));
  if (ruleForm.target_type === "queue") return teamStore.queues.value.filter((item) => item.is_active).map((item) => ({ id: item.id, label: item.name }));
  return teamStore.territories.value.filter((item) => item.is_active).map((item) => ({ id: item.id, label: item.name }));
});

onMounted(async () => {
  try {
    await crmStore.refreshMe();
  } catch {
    profileError.value = "Не удалось загрузить /me. Войдите заново или перезапустите актуальный API.";
  }
  await teamStore.refreshAll();
  if (!visibleTabs.value.some((tab) => tab.id === activeTab.value)) activeTab.value = visibleTabs.value[0]?.id ?? "members";
});

function memberDraft(member: Membership) {
  return memberDrafts[member.id] ??= {
    role: member.role,
    team_id: member.team_id ?? "",
    manager_membership_id: member.manager_membership_id ?? ""
  };
}

function memberName(id: string | null | undefined) {
  return teamStore.members.value.find((item) => item.id === id)?.full_name ?? "Не назначен";
}

function teamName(id: string | null | undefined) {
  return teamStore.teams.value.find((item) => item.id === id)?.name ?? "Без команды";
}

function teamManagerDraft(id: string, managerId: string | null) {
  return teamManagerDrafts[id] ??= managerId ?? "";
}

function queueDraft(id: string, teamId: string | null, strategy: "manual" | "round_robin", membershipIds: string[]) {
  return queueDrafts[id] ??= { team_id: teamId ?? "", strategy, membership_ids: [...membershipIds] };
}

function roleLabel(role: MembershipRole) {
  return roles.find((item) => item.value === role)?.label ?? role;
}

function invitationStatus(item: TeamInvitation) {
  if (item.accepted_at) return "Принято";
  if (item.revoked_at) return "Отозвано";
  if (new Date(item.expires_at).getTime() <= Date.now()) return "Истекло";
  return "Ожидает";
}

async function saveMember(member: Membership) {
  const draft = memberDraft(member);
  await guarded(async () => {
    if (draft.role !== member.role) await teamStore.updateMemberRole(member.id, draft.role);
    if ((draft.team_id || null) !== member.team_id || (draft.manager_membership_id || null) !== member.manager_membership_id) {
      await teamStore.updateMemberStructure(member.id, draft.team_id || null, draft.manager_membership_id || null);
    }
  });
}

async function deactivateMember() {
  if (!deactivationTarget.value || !replacementUserId.value) {
    localError.value = "Выберите участника для переназначения объектов.";
    return;
  }
  await guarded(async () => {
    await teamStore.updateMemberStatus(deactivationTarget.value!.id, false, replacementUserId.value);
    deactivationTarget.value = null;
    replacementUserId.value = "";
  });
}

async function createInvitation() {
  await guarded(async () => {
    await teamStore.createInvitation({
      email: invitationForm.email,
      role: invitationForm.role,
      team_id: invitationForm.team_id || null,
      manager_membership_id: invitationForm.manager_membership_id || null,
      expires_in_hours: invitationForm.expires_in_hours
    });
    invitationForm.email = "";
  });
}

async function copyInvitation(item: TeamInvitation) {
  const link = teamStore.invitationLinks.value[item.id];
  if (!link) {
    localError.value = "Одноразовая ссылка доступна только сразу после создания приглашения.";
    return;
  }
  localError.value = "";
  try {
    await navigator.clipboard.writeText(link);
    teamStore.success.value = "Ссылка скопирована";
  } catch {
    localError.value = "Не удалось скопировать ссылку. Разрешите доступ к буферу обмена.";
  }
}

async function createTeam() {
  await guarded(async () => {
    await teamStore.createTeam({ name: teamForm.name, manager_membership_id: teamForm.manager_membership_id || null });
    teamForm.name = "";
  });
}

async function saveTeam(teamId: string, managerId: string | null) {
  await guarded(() => teamStore.updateTeam(teamId, { manager_membership_id: teamManagerDraft(teamId, managerId) || null }).then(() => undefined));
}

async function createQueue() {
  await guarded(async () => {
    await teamStore.createQueue({
      name: queueForm.name,
      team_id: queueForm.team_id || null,
      strategy: queueForm.strategy,
      membership_ids: queueForm.membership_ids
    });
    queueForm.name = "";
    queueForm.membership_ids = [];
  });
}

async function saveQueue(queueId: string, teamId: string | null, strategy: "manual" | "round_robin", membershipIds: string[]) {
  const draft = queueDraft(queueId, teamId, strategy, membershipIds);
  await guarded(() => teamStore.updateQueue(queueId, { team_id: draft.team_id || null, strategy: draft.strategy, membership_ids: draft.membership_ids }).then(() => undefined));
}

async function revokeInvitation(id: string) {
  await guarded(() => teamStore.revokeInvitation(id).then(() => undefined));
}

async function reactivateMember(id: string) {
  await guarded(() => teamStore.updateMemberStatus(id, true).then(() => undefined));
}

async function toggleTeam(id: string, isActive: boolean) {
  await guarded(() => teamStore.updateTeam(id, { is_active: !isActive }).then(() => undefined));
}

async function toggleQueue(id: string, isActive: boolean) {
  await guarded(() => teamStore.updateQueue(id, { is_active: !isActive }).then(() => undefined));
}

async function claimLead(id: string) {
  await guarded(() => teamStore.claimLead(id).then(() => undefined));
}

async function toggleTerritory(id: string, isActive: boolean) {
  await guarded(() => teamStore.updateTerritory(id, { is_active: !isActive }).then(() => undefined));
}

async function toggleRule(id: string, isActive: boolean) {
  await guarded(() => teamStore.updateAssignmentRule(id, { is_active: !isActive }).then(() => undefined));
}

async function createTerritory() {
  await guarded(async () => {
    await teamStore.createTerritory({
      name: territoryForm.name,
      country_code: territoryForm.country_code || null,
      region: territoryForm.region || null,
      industry: territoryForm.industry || null,
      owner_membership_id: territoryForm.target_type === "member" ? territoryForm.target_id || null : null,
      team_id: territoryForm.target_type === "team" ? territoryForm.target_id || null : null,
      priority: territoryForm.priority
    });
    territoryForm.name = "";
  });
}

async function createRule() {
  await guarded(async () => {
    let criteria: Record<string, string>;
    try {
      const parsed = JSON.parse(ruleForm.criteria) as unknown;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error();
      criteria = Object.fromEntries(Object.entries(parsed).map(([key, value]) => [key, String(value)]));
    } catch {
      localError.value = "Критерии должны быть JSON-объектом.";
      return;
    }
    if (!ruleForm.target_id) {
      localError.value = "Выберите цель назначения.";
      return;
    }
    await teamStore.createAssignmentRule({
      name: ruleForm.name,
      entity_type: ruleForm.entity_type,
      criteria,
      target_type: ruleForm.target_type,
      target_id: ruleForm.target_id,
      priority: ruleForm.priority
    });
    ruleForm.name = "";
  });
}

async function guarded(action: () => Promise<void>) {
  localError.value = "";
  try {
    await action();
  } catch {
    // Store keeps normalized 403/404/409/422 message.
  }
}
</script>

<template>
  <section class="team-page stack">
    <section class="team-hero panel">
      <div><p class="eyebrow">Доступы и маршрутизация</p><h2>Управление командой</h2><p>Участники, структура продаж и правила автоматического назначения.</p></div>
      <button class="secondary" type="button" :disabled="teamStore.loading.value" @click="teamStore.refreshAll">Обновить</button>
    </section>

    <p v-if="!teamStore.canOpen.value" class="team-denied">
      <template v-if="profileError">{{ profileError }}</template>
      <template v-else>Роль <code>{{ crmStore.me.value?.role || "не определена" }}</code> не имеет <code>members:manage</code> или <code>assignments:manage</code>.</template>
    </p>
    <template v-else>
      <nav class="team-tabs" aria-label="Разделы управления командой">
        <button v-for="tab in visibleTabs" :key="tab.id" type="button" :class="{ active: activeTab === tab.id }" @click="activeTab = tab.id">{{ tab.label }}</button>
      </nav>

      <div v-if="teamStore.error.value || localError" class="alert error">{{ localError || teamStore.error.value }}</div>
      <div v-if="teamStore.success.value" class="alert success">{{ teamStore.success.value }}</div>
      <div v-if="teamStore.canManageAssignments.value && !teamStore.canManageMembers.value" class="alert warning">
        Каталог участников недоступен для этой роли: backend требует <code>members:manage</code>. Создание команд и правил доступно, но выбор участников ограничен.
      </div>

      <section v-if="activeTab === 'members'" class="panel team-section">
        <header class="section-head"><div><h2>Участники</h2><p>{{ teamStore.members.value.length }} человек</p></div></header>
        <div class="team-table-scroll"><table class="data-table team-table"><thead><tr><th>Участник</th><th>Роль</th><th>Команда</th><th>Менеджер</th><th>Статус</th><th></th></tr></thead><tbody>
          <tr v-for="member in teamStore.members.value" :key="member.id">
            <td><strong>{{ member.full_name }}</strong><small>{{ member.email }}</small></td>
            <td><select v-model="memberDraft(member).role"><option v-for="role in roles" :key="role.value" :value="role.value">{{ role.label }}</option></select></td>
            <td><select v-model="memberDraft(member).team_id"><option value="">Без команды</option><option v-for="team in teamStore.teams.value" :key="team.id" :value="team.id">{{ team.name }}</option></select></td>
            <td><select v-model="memberDraft(member).manager_membership_id"><option value="">Не назначен</option><option v-for="manager in teamStore.activeMembers.value.filter((item) => item.id !== member.id)" :key="manager.id" :value="manager.id">{{ manager.full_name }}</option></select></td>
            <td><span class="status-pill" :class="{ inactive: !member.is_active }">{{ member.is_active ? "Активен" : "Отключён" }}</span></td>
            <td><div class="row-actions"><button v-if="member.is_active" class="secondary" type="button" @click="saveMember(member)">Сохранить</button><button v-if="member.is_active && member.user_id !== crmStore.me.value?.user_id" class="danger-quiet" type="button" @click="deactivationTarget = member">Деактивировать</button><button v-if="!member.is_active" type="button" @click="reactivateMember(member.id)">Активировать</button></div></td>
          </tr>
        </tbody></table></div>
      </section>

      <section v-else-if="activeTab === 'invitations'" class="team-grid">
        <form class="panel team-form" @submit.prevent="createInvitation"><h2>Новое приглашение</h2><p>Email не отправляется. После создания скопируйте одноразовую ссылку.</p><label>Email<input v-model="invitationForm.email" type="email" required /></label><label>Роль<select v-model="invitationForm.role"><option v-for="role in roles" :key="role.value" :value="role.value">{{ role.label }}</option></select></label><label>Команда<select v-model="invitationForm.team_id"><option value="">Без команды</option><option v-for="team in teamStore.teams.value" :key="team.id" :value="team.id">{{ team.name }}</option></select></label><label>Менеджер<select v-model="invitationForm.manager_membership_id"><option value="">Не назначен</option><option v-for="member in teamStore.activeMembers.value" :key="member.id" :value="member.id">{{ member.full_name }}</option></select></label><label>Срок, часов<input v-model.number="invitationForm.expires_in_hours" type="number" min="1" max="720" required /></label><button type="submit">Создать приглашение</button></form>
        <section class="panel team-list"><h2>Приглашения</h2><article v-for="item in teamStore.invitations.value" :key="item.id" class="management-card"><div><strong>{{ item.email }}</strong><small>{{ roleLabel(item.role) }} · {{ teamName(item.team_id) }} · до {{ new Date(item.expires_at).toLocaleString('ru-RU') }}</small></div><span class="status-pill">{{ invitationStatus(item) }}</span><div class="row-actions"><button v-if="teamStore.invitationLinks.value[item.id]" type="button" @click="copyInvitation(item)">Копировать ссылку</button><button v-if="!item.accepted_at && !item.revoked_at" class="danger-quiet" type="button" @click="revokeInvitation(item.id)">Отозвать</button></div></article><p v-if="!teamStore.invitations.value.length" class="empty">Приглашений нет</p></section>
      </section>

      <section v-else-if="activeTab === 'teams'" class="team-grid">
        <form class="panel team-form" @submit.prevent="createTeam"><h2>Новая команда</h2><label>Название<input v-model="teamForm.name" required minlength="2" /></label><label>Менеджер<select v-model="teamForm.manager_membership_id"><option value="">Не назначен</option><option v-for="member in teamStore.activeMembers.value" :key="member.id" :value="member.id">{{ member.full_name }}</option></select></label><button type="submit">Создать команду</button></form>
        <section class="panel team-list"><h2>Команды</h2><article v-for="team in teamStore.teams.value" :key="team.id" class="management-card"><div><strong>{{ team.name }}</strong><small>Состав: {{ team.member_count }}</small><select :value="teamManagerDraft(team.id, team.manager_membership_id)" @change="teamManagerDrafts[team.id] = ($event.target as HTMLSelectElement).value"><option value="">Без менеджера</option><option v-for="member in teamStore.activeMembers.value" :key="member.id" :value="member.id">{{ member.full_name }}</option></select></div><span class="status-pill" :class="{ inactive: !team.is_active }">{{ team.is_active ? "Активна" : "Отключена" }}</span><div class="row-actions"><button type="button" @click="saveTeam(team.id, team.manager_membership_id)">Сохранить менеджера</button><button class="secondary" type="button" @click="toggleTeam(team.id, team.is_active)">{{ team.is_active ? "Отключить" : "Активировать" }}</button></div><div class="member-chips"><span v-for="member in teamStore.members.value.filter((item) => item.team_id === team.id)" :key="member.id">{{ member.full_name }}</span></div></article><p v-if="!teamStore.teams.value.length" class="empty">Команд нет</p></section>
      </section>

      <section v-else-if="activeTab === 'queues'" class="team-grid">
        <form class="panel team-form" @submit.prevent="createQueue"><h2>Новая очередь</h2><label>Название<input v-model="queueForm.name" required minlength="2" /></label><label>Команда<select v-model="queueForm.team_id"><option value="">Без команды</option><option v-for="team in teamStore.teams.value" :key="team.id" :value="team.id">{{ team.name }}</option></select></label><label>Стратегия<select v-model="queueForm.strategy"><option value="round_robin">Round robin</option><option value="manual">Manual</option></select></label><fieldset><legend>Участники</legend><label v-for="member in teamStore.activeMembers.value" :key="member.id" class="check-row"><input v-model="queueForm.membership_ids" type="checkbox" :value="member.id" />{{ member.full_name }}</label></fieldset><button type="submit">Создать очередь</button></form>
        <section class="panel team-list"><h2>Очереди лидов</h2><article v-for="queue in teamStore.queues.value" :key="queue.id" class="management-card"><div><strong>{{ queue.name }}</strong><small>{{ teamName(queue.team_id) }}</small><details><summary>Настроить стратегию и участников</summary><label>Стратегия<select v-model="queueDraft(queue.id, queue.team_id, queue.strategy, queue.membership_ids).strategy"><option value="round_robin">Round robin</option><option value="manual">Manual</option></select></label><label>Команда<select v-model="queueDraft(queue.id, queue.team_id, queue.strategy, queue.membership_ids).team_id"><option value="">Без команды</option><option v-for="team in teamStore.teams.value" :key="team.id" :value="team.id">{{ team.name }}</option></select></label><label v-for="member in teamStore.activeMembers.value" :key="member.id" class="check-row"><input v-model="queueDraft(queue.id, queue.team_id, queue.strategy, queue.membership_ids).membership_ids" type="checkbox" :value="member.id" />{{ member.full_name }}</label><button type="button" @click="saveQueue(queue.id, queue.team_id, queue.strategy, queue.membership_ids)">Сохранить состав</button></details></div><span class="status-pill" :class="{ inactive: !queue.is_active }">{{ queue.is_active ? "Активна" : "Отключена" }}</span><div class="member-chips"><span v-for="id in queue.membership_ids" :key="id">{{ memberName(id) }}</span></div><div class="row-actions"><button v-if="teamStore.canClaimLead.value && queue.is_active" type="button" @click="claimLead(queue.id)">Забрать лид</button><button class="secondary" type="button" @click="toggleQueue(queue.id, queue.is_active)">{{ queue.is_active ? "Отключить" : "Активировать" }}</button></div></article><p v-if="!teamStore.queues.value.length" class="empty">Очередей нет</p></section>
      </section>

      <section v-else-if="activeTab === 'territories'" class="team-grid">
        <form class="panel team-form" @submit.prevent="createTerritory"><h2>Новая территория</h2><label>Название<input v-model="territoryForm.name" required minlength="2" /></label><div class="form-pair"><label>Страна<input v-model="territoryForm.country_code" maxlength="2" placeholder="RU" /></label><label>Регион<input v-model="territoryForm.region" /></label></div><label>Отрасль<input v-model="territoryForm.industry" /></label><label>Цель<select v-model="territoryForm.target_type"><option value="member">Владелец</option><option value="team">Команда</option></select></label><label>{{ territoryForm.target_type === 'member' ? 'Владелец' : 'Команда' }}<select v-model="territoryForm.target_id"><option value="">Не назначено</option><option v-for="item in territoryForm.target_type === 'member' ? teamStore.activeMembers.value : teamStore.teams.value" :key="item.id" :value="item.id">{{ 'full_name' in item ? item.full_name : item.name }}</option></select></label><label>Приоритет<input v-model.number="territoryForm.priority" type="number" min="0" max="10000" /></label><button type="submit">Создать территорию</button></form>
        <section class="panel team-list"><h2>Территории</h2><article v-for="territory in teamStore.territories.value" :key="territory.id" class="management-card"><div><strong>{{ territory.name }}</strong><small>{{ territory.country_code || 'Все страны' }} · {{ territory.region || 'Все регионы' }} · {{ territory.industry || 'Все отрасли' }}</small><small>Цель: {{ territory.owner_membership_id ? memberName(territory.owner_membership_id) : teamName(territory.team_id) }} · приоритет {{ territory.priority }}</small></div><span class="status-pill" :class="{ inactive: !territory.is_active }">{{ territory.is_active ? "Активна" : "Отключена" }}</span><button class="secondary" type="button" @click="toggleTerritory(territory.id, territory.is_active)">{{ territory.is_active ? "Отключить" : "Активировать" }}</button></article><p v-if="!teamStore.territories.value.length" class="empty">Территорий нет</p></section>
      </section>

      <section v-else class="team-grid">
        <form class="panel team-form" @submit.prevent="createRule"><h2>Новое правило</h2><label>Название<input v-model="ruleForm.name" required minlength="2" /></label><label>Тип объекта<select v-model="ruleForm.entity_type"><option value="lead">Лид</option><option value="company">Компания</option></select></label><label>Критерии, JSON<textarea v-model="ruleForm.criteria" rows="4" required></textarea></label><label>Тип цели<select v-model="ruleForm.target_type" @change="ruleForm.target_id = ''"><option value="member">Участник</option><option value="team">Команда</option><option value="queue">Очередь</option><option value="territory">Территория</option></select></label><label>Цель<select v-model="ruleForm.target_id" required><option value="">Выберите</option><option v-for="item in ruleTargets" :key="item.id" :value="item.id">{{ item.label }}</option></select></label><label>Приоритет<input v-model.number="ruleForm.priority" type="number" min="0" max="10000" /></label><button type="submit">Создать правило</button></form>
        <section class="panel team-list"><h2>Правила назначения</h2><article v-for="rule in teamStore.assignmentRules.value" :key="rule.id" class="management-card"><div><strong>{{ rule.name }}</strong><small>{{ rule.entity_type }} · {{ JSON.stringify(rule.criteria) }}</small><small>{{ rule.target_type }} · приоритет {{ rule.priority }}</small></div><span class="status-pill" :class="{ inactive: !rule.is_active }">{{ rule.is_active ? "Активно" : "Отключено" }}</span><button class="secondary" type="button" @click="toggleRule(rule.id, rule.is_active)">{{ rule.is_active ? "Отключить" : "Активировать" }}</button></article><p v-if="!teamStore.assignmentRules.value.length" class="empty">Правил нет</p></section>
      </section>
    </template>

    <div v-if="deactivationTarget" class="team-modal-backdrop" @click.self="deactivationTarget = null">
      <section class="team-modal" role="dialog" aria-modal="true" aria-labelledby="deactivate-title"><h2 id="deactivate-title">Деактивировать {{ deactivationTarget.full_name }}?</h2><p>Все компании, контакты, лиды, сделки, задачи и следующие действия будут переназначены.</p><label>Новый ответственный<select v-model="replacementUserId" required><option value="">Выберите участника</option><option v-for="member in replacementMembers" :key="member.id" :value="member.user_id">{{ member.full_name }}</option></select></label><div class="row-actions"><button class="danger-button" type="button" :disabled="!replacementUserId" @click="deactivateMember">Деактивировать и переназначить</button><button class="secondary" type="button" @click="deactivationTarget = null">Отмена</button></div></section>
    </div>
  </section>
</template>

<style scoped>
.team-page{padding-bottom:36px}.team-hero{display:flex;align-items:center;justify-content:space-between;gap:20px}.team-hero h2{margin:3px 0 6px;font-size:25px}.team-hero p:last-child,.section-head p,.team-form>p{margin:0;color:var(--muted)}.team-tabs{display:flex;gap:4px;overflow-x:auto;border:1px solid var(--line);border-radius:10px;padding:4px;background:var(--surface)}.team-tabs button{min-height:36px;color:var(--muted);background:transparent;white-space:nowrap}.team-tabs button.active{color:var(--text);background:#fff;box-shadow:0 1px 5px rgb(0 0 0/10%)}.team-denied{border:1px solid #efc2c2;border-radius:10px;padding:18px;color:#8f2525;background:#fff6f6}.alert.warning{color:#7a4a0a;border-color:#f2d39e;background:#fff8e8}.team-section{padding:0;overflow:hidden}.section-head{padding:18px}.section-head h2,.team-form h2,.team-list h2{margin:0 0 5px}.team-table-scroll{overflow-x:auto}.team-table{min-width:1060px}.team-table td strong,.team-table td small{display:block}.team-table td small{margin-top:3px;color:var(--muted)}.team-table select{min-width:150px}.row-actions{display:flex;flex-wrap:wrap;gap:7px}.danger-quiet,.danger-button{color:#a02929;border-color:#efc2c2;background:#fff6f6}.team-grid{display:grid;grid-template-columns:minmax(280px,360px) minmax(0,1fr);gap:16px;align-items:start}.team-form{display:grid;gap:13px}.team-form label{margin:0}.team-form fieldset{display:grid;gap:7px;border:1px solid var(--line);border-radius:8px;padding:10px}.team-form legend{padding:0 5px;font-weight:700}.check-row{display:flex;align-items:center;gap:8px}.form-pair{display:grid;grid-template-columns:1fr 1fr;gap:8px}.team-list{display:grid;gap:10px}.management-card{display:grid;grid-template-columns:minmax(180px,1fr) auto auto;gap:12px;align-items:center;border:1px solid var(--line);border-radius:9px;padding:13px}.management-card>div:first-child{display:grid;gap:4px}.management-card small{color:var(--muted)}.member-chips{display:flex;grid-column:1/-1;flex-wrap:wrap;gap:5px}.member-chips span{border-radius:99px;padding:5px 8px;color:#34516f;background:#edf5ff;font-size:11px}.status-pill{display:inline-flex;border-radius:99px;padding:5px 8px;color:#17663a;background:#e9f8ef;font-size:11px;font-weight:700;white-space:nowrap}.status-pill.inactive{color:#7c5660;background:#f3edef}.team-modal-backdrop{position:fixed;inset:0;z-index:120;display:grid;place-items:center;padding:18px;background:rgb(15 23 42/38%);backdrop-filter:blur(2px)}.team-modal{display:grid;gap:14px;width:min(500px,100%);border-radius:14px;padding:24px;background:#fff;box-shadow:0 24px 70px rgb(15 23 42/24%)}.team-modal h2,.team-modal p{margin:0}.team-modal p{color:var(--muted)}@media(max-width:920px){.team-grid{grid-template-columns:1fr}.management-card{grid-template-columns:minmax(0,1fr) auto}.management-card .row-actions,.management-card>button{grid-column:1/-1}}@media(max-width:620px){.team-hero{align-items:stretch;flex-direction:column}.form-pair{grid-template-columns:1fr}.management-card{grid-template-columns:1fr}.management-card>*{grid-column:1!important}}
</style>
