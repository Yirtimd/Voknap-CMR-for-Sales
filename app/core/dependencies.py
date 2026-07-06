from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.modules.accounts.models import Membership, User


bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentTenant:
    id: UUID
    user_id: UUID
    role: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


def get_current_tenant(
    x_tenant_id: UUID = Header(alias="X-Tenant-Id"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CurrentTenant:
    membership = (
        db.query(Membership)
        .filter(Membership.tenant_id == x_tenant_id, Membership.user_id == user.id)
        .one_or_none()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied")

    return CurrentTenant(id=x_tenant_id, user_id=user.id, role=membership.role)

