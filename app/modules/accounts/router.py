from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentTenant
from app.core.rbac import Permission, Role, deny_access, require_permission
from app.modules.accounts.models import Membership, User
from app.modules.accounts.schemas import (
    MembershipCreate,
    MembershipResponse,
    MembershipRoleUpdate,
)


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

    membership = Membership(tenant_id=tenant.id, user_id=user.id, role=payload.role)
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
            .filter(Membership.tenant_id == tenant.id, Membership.role == Role.OWNER)
            .count()
        )
        if owner_count == 1:
            deny_access("The last owner cannot be demoted")

    membership.role = payload.role
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
        created_at=membership.created_at,
    )


def _require_role_grant_allowed(actor_role: Role, target_role: Role) -> None:
    if actor_role is Role.ADMIN and target_role in {Role.OWNER, Role.ADMIN}:
        deny_access("Only an owner can grant privileged roles")
