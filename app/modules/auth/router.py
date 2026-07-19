import hashlib
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db, set_tenant_context
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.accounts.models import Membership, TeamInvitation, Tenant, User
from app.modules.accounts.schemas import InvitationAccept, InvitationAcceptResponse
from app.modules.auth.schemas import AuthResponse, LoginRequest, RegisterCompanyRequest, TenantResponse


router = APIRouter()


@router.post("/register-company", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_company(payload: RegisterCompanyRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing_user = db.query(User).filter(User.email == payload.owner_email).one_or_none()
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    existing_tenant = db.query(Tenant).filter(Tenant.slug == payload.company_slug).one_or_none()
    if existing_tenant is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company slug already used")

    tenant = Tenant(name=payload.company_name, slug=payload.company_slug)
    user = User(
        email=payload.owner_email,
        full_name=payload.owner_full_name,
        password_hash=hash_password(payload.owner_password),
    )
    db.add_all([tenant, user])
    db.flush()

    membership = Membership(tenant_id=tenant.id, user_id=user.id, role="owner")
    db.add(membership)
    db.commit()
    db.refresh(tenant)
    db.refresh(user)

    return AuthResponse(
        access_token=create_access_token(user.id),
        user_id=user.id,
        tenants=[TenantResponse.model_validate(tenant)],
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    tenants = [
        membership.tenant
        for membership in user.memberships
        if membership.is_active and membership.tenant.is_active
    ]
    return AuthResponse(
        access_token=create_access_token(user.id),
        user_id=user.id,
        tenants=[TenantResponse.model_validate(tenant) for tenant in tenants],
    )


@router.post("/invitations/accept", response_model=InvitationAcceptResponse)
def accept_invitation(
    payload: InvitationAccept,
    db: Session = Depends(get_db),
) -> InvitationAcceptResponse:
    try:
        tenant_id = UUID(payload.token.split(".", 1)[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=404, detail="Invitation not found") from None
    set_tenant_context(db, tenant_id)
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    invitation = (
        db.query(TeamInvitation)
        .filter(
            TeamInvitation.tenant_id == tenant_id,
            TeamInvitation.token_hash == token_hash,
        )
        .one_or_none()
    )
    now = datetime.now(timezone.utc)
    if (
        invitation is None
        or invitation.accepted_at is not None
        or invitation.revoked_at is not None
        or _as_utc(invitation.expires_at) <= now
    ):
        raise HTTPException(status_code=404, detail="Invitation not found")

    user = db.query(User).filter(User.email == invitation.email).one_or_none()
    if user is None:
        if payload.full_name is None:
            raise HTTPException(status_code=422, detail="full_name is required for a new user")
        user = User(
            email=invitation.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        db.flush()
    elif not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    elif not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    existing = (
        db.query(Membership)
        .filter(Membership.tenant_id == tenant_id, Membership.user_id == user.id)
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="User is already a member")
    db.add(
        Membership(
            tenant_id=tenant_id,
            user_id=user.id,
            role=invitation.role,
            team_id=invitation.team_id,
            manager_membership_id=invitation.manager_membership_id,
            is_active=True,
        )
    )
    invitation.accepted_at = now
    db.commit()
    return InvitationAcceptResponse(
        access_token=create_access_token(user.id),
        user_id=user.id,
        tenant_id=tenant_id,
    )


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
