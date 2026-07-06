from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.accounts.models import Membership, Tenant, User
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

    tenants = [membership.tenant for membership in user.memberships if membership.tenant.is_active]
    return AuthResponse(
        access_token=create_access_token(user.id),
        user_id=user.id,
        tenants=[TenantResponse.model_validate(tenant) for tenant in tenants],
    )

