import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentTenant
from app.core.rbac import Permission, Role, has_permission, require_permission
from app.modules.accounts.assignment import validate_criteria, validate_target
from app.modules.accounts.models import (
    AssignmentRule,
    LeadQueue,
    LeadQueueMember,
    Membership,
    SalesTeam,
    TeamInvitation,
    Territory,
)
from app.modules.accounts.router import _get_membership, _require_role_grant_allowed
from app.modules.accounts.schemas import (
    AssignmentRuleCreate,
    AssignmentRuleResponse,
    AssignmentRuleUpdate,
    InvitationCreate,
    InvitationResponse,
    QueueCreate,
    QueueResponse,
    QueueUpdate,
    TeamCreate,
    TeamResponse,
    TeamUpdate,
    TerritoryCreate,
    TerritoryResponse,
    TerritoryUpdate,
)
from app.modules.sales.models import Lead
from app.modules.sales.schemas import LeadResponse


router = APIRouter()


@router.post("/invitations", response_model=InvitationResponse, status_code=201)
def create_invitation(
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.MEMBERS_MANAGE)),
) -> InvitationResponse:
    _require_role_grant_allowed(tenant.role, payload.role)
    _validate_team_and_manager(db, tenant.id, payload.team_id, payload.manager_membership_id)
    existing = (
        db.query(TeamInvitation)
        .filter(
            TeamInvitation.tenant_id == tenant.id,
            TeamInvitation.email == payload.email.lower(),
            TeamInvitation.accepted_at.is_(None),
            TeamInvitation.revoked_at.is_(None),
        )
        .one_or_none()
    )
    if existing is not None and _as_utc(existing.expires_at) > datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Active invitation already exists")

    token = f"{tenant.id}.{secrets.token_urlsafe(32)}"
    invitation = TeamInvitation(
        tenant_id=tenant.id,
        email=payload.email.lower(),
        role=payload.role,
        team_id=payload.team_id,
        manager_membership_id=payload.manager_membership_id,
        token_hash=_token_hash(token),
        invited_by_id=tenant.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=payload.expires_in_hours),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return _invitation_response(invitation, token)


@router.get("/invitations", response_model=list[InvitationResponse])
def list_invitations(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.MEMBERS_MANAGE)),
) -> list[InvitationResponse]:
    rows = (
        db.query(TeamInvitation)
        .filter(TeamInvitation.tenant_id == tenant.id)
        .order_by(TeamInvitation.created_at.desc())
        .all()
    )
    return [_invitation_response(row) for row in rows]


@router.delete("/invitations/{invitation_id}", status_code=204)
def revoke_invitation(
    invitation_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.MEMBERS_MANAGE)),
) -> None:
    invitation = _get(db, TeamInvitation, tenant.id, invitation_id, "Invitation")
    if invitation.accepted_at is not None:
        raise HTTPException(status_code=409, detail="Accepted invitation cannot be revoked")
    invitation.revoked_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/teams", response_model=TeamResponse, status_code=201)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.ASSIGNMENTS_MANAGE)),
) -> TeamResponse:
    if payload.manager_membership_id is not None:
        _get_active_member(db, tenant.id, payload.manager_membership_id)
    team = SalesTeam(tenant_id=tenant.id, **payload.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return _team_response(db, team)


@router.get("/teams", response_model=list[TeamResponse])
def list_teams(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.ASSIGNMENTS_MANAGE)),
) -> list[TeamResponse]:
    return [
        _team_response(db, row)
        for row in db.query(SalesTeam)
        .filter(SalesTeam.tenant_id == tenant.id)
        .order_by(SalesTeam.name)
        .all()
    ]


@router.patch("/teams/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: UUID,
    payload: TeamUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.ASSIGNMENTS_MANAGE)),
) -> TeamResponse:
    team = _get(db, SalesTeam, tenant.id, team_id, "Team")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("manager_membership_id") is not None:
        _get_active_member(db, tenant.id, changes["manager_membership_id"])
    for key, value in changes.items():
        setattr(team, key, value)
    db.commit()
    db.refresh(team)
    return _team_response(db, team)


@router.post("/queues", response_model=QueueResponse, status_code=201)
def create_queue(
    payload: QueueCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.ASSIGNMENTS_MANAGE)),
) -> QueueResponse:
    if payload.team_id is not None:
        _get(db, SalesTeam, tenant.id, payload.team_id, "Team")
    queue = LeadQueue(tenant_id=tenant.id, **payload.model_dump(exclude={"membership_ids"}))
    db.add(queue)
    db.flush()
    _replace_queue_members(db, tenant.id, queue.id, payload.membership_ids)
    db.commit()
    db.refresh(queue)
    return _queue_response(db, queue)


@router.get("/queues", response_model=list[QueueResponse])
def list_queues(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.ASSIGNMENTS_MANAGE)),
) -> list[QueueResponse]:
    rows = db.query(LeadQueue).filter(LeadQueue.tenant_id == tenant.id).order_by(LeadQueue.name).all()
    return [_queue_response(db, row) for row in rows]


@router.patch("/queues/{queue_id}", response_model=QueueResponse)
def update_queue(
    queue_id: UUID,
    payload: QueueUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.ASSIGNMENTS_MANAGE)),
) -> QueueResponse:
    queue = _get(db, LeadQueue, tenant.id, queue_id, "Queue")
    changes = payload.model_dump(exclude_unset=True, exclude={"membership_ids"})
    if changes.get("team_id") is not None:
        _get(db, SalesTeam, tenant.id, changes["team_id"], "Team")
    for key, value in changes.items():
        setattr(queue, key, value)
    if payload.membership_ids is not None:
        _replace_queue_members(db, tenant.id, queue.id, payload.membership_ids)
    db.commit()
    db.refresh(queue)
    return _queue_response(db, queue)


@router.post("/queues/{queue_id}/claim", response_model=LeadResponse)
def claim_queue_lead(
    queue_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.CRM_WRITE)),
) -> Lead:
    queue = _get(db, LeadQueue, tenant.id, queue_id, "Queue")
    membership = (
        db.query(Membership)
        .filter(
            Membership.tenant_id == tenant.id,
            Membership.user_id == tenant.user_id,
            Membership.is_active.is_(True),
        )
        .one()
    )
    queue_member = (
        db.query(LeadQueueMember)
        .filter(
            LeadQueueMember.tenant_id == tenant.id,
            LeadQueueMember.queue_id == queue.id,
            LeadQueueMember.membership_id == membership.id,
            LeadQueueMember.is_active.is_(True),
        )
        .one_or_none()
    )
    if queue_member is None and not has_permission(tenant.role, Permission.ASSIGNMENTS_MANAGE):
        raise HTTPException(status_code=403, detail="Queue access denied")
    lead = (
        db.query(Lead)
        .filter(
            Lead.tenant_id == tenant.id,
            Lead.queue_id == queue.id,
            Lead.owner_id.is_(None),
        )
        .order_by(Lead.created_at)
        .with_for_update(skip_locked=True)
        .first()
    )
    if lead is None:
        raise HTTPException(status_code=404, detail="No unassigned leads in queue")
    lead.owner_id = tenant.user_id
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/territories", response_model=TerritoryResponse, status_code=201)
def create_territory(
    payload: TerritoryCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.ASSIGNMENTS_MANAGE)),
) -> Territory:
    _validate_territory_targets(db, tenant.id, payload.owner_membership_id, payload.team_id)
    territory = Territory(tenant_id=tenant.id, **_normalized_territory(payload.model_dump()))
    db.add(territory)
    db.commit()
    db.refresh(territory)
    return territory


@router.get("/territories", response_model=list[TerritoryResponse])
def list_territories(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.ASSIGNMENTS_MANAGE)),
) -> list[Territory]:
    return (
        db.query(Territory)
        .filter(Territory.tenant_id == tenant.id)
        .order_by(Territory.priority, Territory.name)
        .all()
    )


@router.patch("/territories/{territory_id}", response_model=TerritoryResponse)
def update_territory(
    territory_id: UUID,
    payload: TerritoryUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.ASSIGNMENTS_MANAGE)),
) -> Territory:
    territory = _get(db, Territory, tenant.id, territory_id, "Territory")
    changes = _normalized_territory(payload.model_dump(exclude_unset=True))
    _validate_territory_targets(
        db,
        tenant.id,
        changes.get("owner_membership_id", territory.owner_membership_id),
        changes.get("team_id", territory.team_id),
    )
    for key, value in changes.items():
        setattr(territory, key, value)
    db.commit()
    db.refresh(territory)
    return territory


@router.post("/assignment-rules", response_model=AssignmentRuleResponse, status_code=201)
def create_assignment_rule(
    payload: AssignmentRuleCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.ASSIGNMENTS_MANAGE)),
) -> AssignmentRuleResponse:
    validate_criteria(payload.entity_type, payload.criteria)
    validate_target(db, tenant.id, payload.target_type, payload.target_id)
    rule = AssignmentRule(
        tenant_id=tenant.id,
        name=payload.name,
        entity_type=payload.entity_type,
        criteria_json=json.dumps(payload.criteria, sort_keys=True),
        target_type=payload.target_type,
        priority=payload.priority,
        **_target_columns(payload.target_type, payload.target_id),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_response(rule)


@router.get("/assignment-rules", response_model=list[AssignmentRuleResponse])
def list_assignment_rules(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.ASSIGNMENTS_MANAGE)),
) -> list[AssignmentRuleResponse]:
    rows = (
        db.query(AssignmentRule)
        .filter(AssignmentRule.tenant_id == tenant.id)
        .order_by(AssignmentRule.priority, AssignmentRule.created_at)
        .all()
    )
    return [_rule_response(row) for row in rows]


@router.patch("/assignment-rules/{rule_id}", response_model=AssignmentRuleResponse)
def update_assignment_rule(
    rule_id: UUID,
    payload: AssignmentRuleUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.ASSIGNMENTS_MANAGE)),
) -> AssignmentRuleResponse:
    rule = _get(db, AssignmentRule, tenant.id, rule_id, "Assignment rule")
    changes = payload.model_dump(exclude_unset=True)
    criteria = changes.pop("criteria", None)
    if criteria is not None:
        validate_criteria(rule.entity_type, criteria)
        rule.criteria_json = json.dumps(criteria, sort_keys=True)
    target_type = changes.pop("target_type", rule.target_type)
    target_id = changes.pop("target_id", None)
    if target_id is not None or target_type != rule.target_type:
        if target_id is None:
            target_id = _rule_target_id(rule)
        validate_target(db, tenant.id, target_type, target_id)
        rule.target_type = target_type
        for key, value in _target_columns(target_type, target_id).items():
            setattr(rule, key, value)
    for key, value in changes.items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return _rule_response(rule)


def _get(db: Session, model, tenant_id: UUID, object_id: UUID, label: str):
    row = db.query(model).filter(model.tenant_id == tenant_id, model.id == object_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return row


def _get_active_member(db: Session, tenant_id: UUID, membership_id: UUID) -> Membership:
    member = _get_membership(db, tenant_id, membership_id)
    if not member.is_active:
        raise HTTPException(status_code=409, detail="Member is inactive")
    return member


def _validate_team_and_manager(
    db: Session,
    tenant_id: UUID,
    team_id: UUID | None,
    manager_id: UUID | None,
) -> None:
    if team_id is not None:
        team = _get(db, SalesTeam, tenant_id, team_id, "Team")
        if not team.is_active:
            raise HTTPException(status_code=409, detail="Team is inactive")
    if manager_id is not None:
        _get_active_member(db, tenant_id, manager_id)


def _replace_queue_members(
    db: Session,
    tenant_id: UUID,
    queue_id: UUID,
    membership_ids: list[UUID],
) -> None:
    unique_ids = list(dict.fromkeys(membership_ids))
    for membership_id in unique_ids:
        _get_active_member(db, tenant_id, membership_id)
    db.query(LeadQueueMember).filter(
        LeadQueueMember.tenant_id == tenant_id,
        LeadQueueMember.queue_id == queue_id,
    ).delete(synchronize_session=False)
    db.add_all(
        LeadQueueMember(tenant_id=tenant_id, queue_id=queue_id, membership_id=member_id)
        for member_id in unique_ids
    )


def _validate_territory_targets(
    db: Session,
    tenant_id: UUID,
    owner_membership_id: UUID | None,
    team_id: UUID | None,
) -> None:
    if owner_membership_id is not None and team_id is not None:
        raise HTTPException(status_code=422, detail="Choose either territory owner or team")
    if owner_membership_id is not None:
        _get_active_member(db, tenant_id, owner_membership_id)
    if team_id is not None:
        _get(db, SalesTeam, tenant_id, team_id, "Team")


def _normalized_territory(values: dict) -> dict:
    if values.get("country_code") is not None:
        values["country_code"] = values["country_code"].upper()
    return values


def _target_columns(target_type: str, target_id: UUID) -> dict:
    values = {"assignee_id": None, "team_id": None, "queue_id": None, "territory_id": None}
    column = {"member": "assignee_id", "team": "team_id", "queue": "queue_id", "territory": "territory_id"}[target_type]
    values[column] = target_id
    return values


def _rule_target_id(rule: AssignmentRule) -> UUID:
    value = {
        "member": rule.assignee_id,
        "team": rule.team_id,
        "queue": rule.queue_id,
        "territory": rule.territory_id,
    }[rule.target_type]
    assert value is not None
    return value


def _rule_response(rule: AssignmentRule) -> AssignmentRuleResponse:
    return AssignmentRuleResponse(
        id=rule.id,
        name=rule.name,
        entity_type=rule.entity_type,
        criteria=json.loads(rule.criteria_json),
        target_type=rule.target_type,
        target_id=_rule_target_id(rule),
        priority=rule.priority,
        is_active=rule.is_active,
        created_at=rule.created_at,
    )


def _team_response(db: Session, team: SalesTeam) -> TeamResponse:
    count = db.query(Membership).filter(Membership.tenant_id == team.tenant_id, Membership.team_id == team.id).count()
    return TeamResponse(
        id=team.id,
        name=team.name,
        manager_membership_id=team.manager_membership_id,
        is_active=team.is_active,
        member_count=count,
        created_at=team.created_at,
    )


def _queue_response(db: Session, queue: LeadQueue) -> QueueResponse:
    member_ids = [
        row.membership_id
        for row in db.query(LeadQueueMember)
        .filter(LeadQueueMember.tenant_id == queue.tenant_id, LeadQueueMember.queue_id == queue.id)
        .order_by(LeadQueueMember.created_at)
        .all()
    ]
    return QueueResponse(
        id=queue.id,
        name=queue.name,
        team_id=queue.team_id,
        strategy=queue.strategy,
        membership_ids=member_ids,
        is_active=queue.is_active,
        created_at=queue.created_at,
    )


def _invitation_response(invitation: TeamInvitation, token: str | None = None) -> InvitationResponse:
    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=Role(invitation.role),
        team_id=invitation.team_id,
        manager_membership_id=invitation.manager_membership_id,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        revoked_at=invitation.revoked_at,
        created_at=invitation.created_at,
        token=token,
    )


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
