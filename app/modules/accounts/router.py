from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentTenant
from app.core.rbac import Permission, Role, deny_access, require_permission
from app.modules.accounts.models import Membership, SalesTeam, User
from app.modules.accounts.schemas import (
    MembershipCreate,
    MembershipResponse,
    MembershipRoleUpdate,
    MembershipStatusUpdate,
    MembershipStructureUpdate,
)
from app.modules.sales.models import Company, Contact, Deal, Lead, NextAction, Task


router = APIRouter()


@router.post("/members", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    payload: MembershipCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.MEMBERS_MANAGE)),
) -> MembershipResponse:
    _require_role_grant_allowed(tenant.role, payload.role)
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active user not found")
    existing = (
        db.query(Membership)
        .filter(Membership.tenant_id == tenant.id, Membership.user_id == user.id)
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member")

    _validate_structure(db, tenant.id, payload.team_id, payload.manager_membership_id)
    membership = Membership(
        tenant_id=tenant.id,
        user_id=user.id,
        role=payload.role,
        team_id=payload.team_id,
        manager_membership_id=payload.manager_membership_id,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return _membership_response(membership)


@router.get("/members", response_model=list[MembershipResponse])
def list_members(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.MEMBERS_MANAGE)),
) -> list[MembershipResponse]:
    memberships = (
        db.query(Membership)
        .filter(Membership.tenant_id == tenant.id)
        .order_by(Membership.created_at)
        .all()
    )
    return [_membership_response(membership) for membership in memberships]


@router.patch("/members/{membership_id}", response_model=MembershipResponse)
def update_member_role(
    membership_id: UUID,
    payload: MembershipRoleUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.MEMBERS_MANAGE)),
) -> MembershipResponse:
    membership = (
        db.query(Membership)
        .filter(Membership.id == membership_id, Membership.tenant_id == tenant.id)
        .one_or_none()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

    if tenant.role is Role.ADMIN:
        if membership.role in {Role.OWNER, Role.ADMIN} or payload.role in {Role.OWNER, Role.ADMIN}:
            deny_access("Only an owner can manage privileged roles")

    if membership.role == Role.OWNER and payload.role != Role.OWNER:
        owner_count = (
            db.query(Membership)
            .filter(
                Membership.tenant_id == tenant.id,
                Membership.role == Role.OWNER,
                Membership.is_active.is_(True),
            )
            .count()
        )
        if owner_count == 1:
            deny_access("The last owner cannot be demoted")

    membership.role = payload.role
    db.commit()
    db.refresh(membership)
    return _membership_response(membership)


@router.patch("/members/{membership_id}/structure", response_model=MembershipResponse)
def update_member_structure(
    membership_id: UUID,
    payload: MembershipStructureUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.MEMBERS_MANAGE)),
) -> MembershipResponse:
    membership = _get_membership(db, tenant.id, membership_id)
    if payload.manager_membership_id == membership.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A member cannot manage themselves")
    _validate_structure(db, tenant.id, payload.team_id, payload.manager_membership_id)
    if payload.manager_membership_id is not None:
        _ensure_no_manager_cycle(db, membership, payload.manager_membership_id)
    membership.team_id = payload.team_id
    membership.manager_membership_id = payload.manager_membership_id
    db.commit()
    db.refresh(membership)
    return _membership_response(membership)


@router.patch("/members/{membership_id}/status", response_model=MembershipResponse)
def update_member_status(
    membership_id: UUID,
    payload: MembershipStatusUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.MEMBERS_MANAGE)),
) -> MembershipResponse:
    membership = _get_membership(db, tenant.id, membership_id)
    if tenant.role is Role.ADMIN and membership.role in {Role.OWNER, Role.ADMIN}:
        deny_access("Only an owner can manage privileged roles")
    if membership.user_id == tenant.user_id and not payload.is_active:
        deny_access("You cannot deactivate your own membership")
    if membership.role == Role.OWNER and not payload.is_active:
        _require_another_owner(db, tenant.id, membership.id)

    if not payload.is_active:
        _reassign_owned_records(db, tenant.id, membership.user_id, payload.reassign_to_user_id)
        membership.is_active = False
        membership.deactivated_at = datetime.now(timezone.utc)
        membership.deactivated_by_id = tenant.user_id
    else:
        membership.is_active = True
        membership.deactivated_at = None
        membership.deactivated_by_id = None
    db.commit()
    db.refresh(membership)
    return _membership_response(membership)


def _membership_response(membership: Membership) -> MembershipResponse:
    return MembershipResponse(
        id=membership.id,
        user_id=membership.user_id,
        email=membership.user.email,
        full_name=membership.user.full_name,
        role=Role(membership.role),
        is_active=membership.is_active,
        team_id=membership.team_id,
        manager_membership_id=membership.manager_membership_id,
        deactivated_at=membership.deactivated_at,
        created_at=membership.created_at,
    )


def _require_role_grant_allowed(actor_role: Role, target_role: Role) -> None:
    if actor_role is Role.ADMIN and target_role in {Role.OWNER, Role.ADMIN}:
        deny_access("Only an owner can grant privileged roles")


def _get_membership(db: Session, tenant_id: UUID, membership_id: UUID) -> Membership:
    membership = (
        db.query(Membership)
        .filter(Membership.tenant_id == tenant_id, Membership.id == membership_id)
        .one_or_none()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    return membership


def _validate_structure(
    db: Session,
    tenant_id: UUID,
    team_id: UUID | None,
    manager_membership_id: UUID | None,
) -> None:
    if team_id is not None:
        team = db.query(SalesTeam).filter(SalesTeam.tenant_id == tenant_id, SalesTeam.id == team_id).one_or_none()
        if team is None or not team.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active team not found")
    if manager_membership_id is not None:
        manager = _get_membership(db, tenant_id, manager_membership_id)
        if not manager.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Manager is inactive")


def _ensure_no_manager_cycle(
    db: Session,
    membership: Membership,
    manager_membership_id: UUID,
) -> None:
    visited = {membership.id}
    current_id: UUID | None = manager_membership_id
    while current_id is not None:
        if current_id in visited:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Manager hierarchy cycle")
        visited.add(current_id)
        current = _get_membership(db, membership.tenant_id, current_id)
        current_id = current.manager_membership_id


def _require_another_owner(db: Session, tenant_id: UUID, membership_id: UUID) -> None:
    owner_count = (
        db.query(Membership)
        .filter(
            Membership.tenant_id == tenant_id,
            Membership.role == Role.OWNER,
            Membership.is_active.is_(True),
            Membership.id != membership_id,
        )
        .count()
    )
    if owner_count == 0:
        deny_access("The last owner cannot be deactivated")


def _reassign_owned_records(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    replacement_user_id: UUID | None,
) -> None:
    owned = sum(
        db.query(model)
        .filter(model.tenant_id == tenant_id, getattr(model, field) == user_id)
        .count()
        for model, field in (
            (Company, "owner_id"),
            (Contact, "owner_id"),
            (Lead, "owner_id"),
            (Deal, "owner_id"),
            (Task, "assigned_to_id"),
            (NextAction, "assigned_to_id"),
        )
    )
    if owned and replacement_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Member owns CRM records; reassign_to_user_id is required",
        )
    if replacement_user_id is None:
        return
    replacement = (
        db.query(Membership)
        .filter(
            Membership.tenant_id == tenant_id,
            Membership.user_id == replacement_user_id,
            Membership.is_active.is_(True),
        )
        .one_or_none()
    )
    if replacement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active replacement not found")
    for model, field in (
        (Company, "owner_id"),
        (Contact, "owner_id"),
        (Lead, "owner_id"),
        (Deal, "owner_id"),
        (Task, "assigned_to_id"),
        (NextAction, "assigned_to_id"),
    ):
        db.query(model).filter(
            model.tenant_id == tenant_id, getattr(model, field) == user_id
        ).update({field: replacement_user_id}, synchronize_session=False)
