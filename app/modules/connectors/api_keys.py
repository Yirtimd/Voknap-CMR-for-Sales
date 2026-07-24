import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db, set_tenant_context
from app.modules.connectors.models import PublicApiKey


ALLOWED_SCOPES = {"leads:read", "leads:write"}


@dataclass(frozen=True)
class PublicApiPrincipal:
    tenant_id: UUID
    key_id: UUID
    scopes: frozenset[str]

    def require(self, scope: str) -> None:
        if scope not in self.scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key scope denied")


def create_api_key(
    db: Session,
    *,
    tenant_id: UUID,
    title: str,
    scopes: list[str],
    expires_at: datetime | None,
    created_by_id: UUID,
) -> tuple[PublicApiKey, str]:
    invalid = sorted(set(scopes) - ALLOWED_SCOPES)
    if invalid:
        raise ValueError(f"Unsupported API key scopes: {', '.join(invalid)}")
    raw_secret = secrets.token_urlsafe(32)
    raw_key = f"voknap_live_{tenant_id.hex}_{raw_secret}"
    key = PublicApiKey(
        tenant_id=tenant_id,
        title=title,
        key_prefix=raw_key[:24],
        key_hash=_hash(raw_key),
        scopes_json=json.dumps(sorted(set(scopes))),
        expires_at=expires_at,
        created_by_id=created_by_id,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key, raw_key


def get_public_api_principal(
    x_api_key: str = Header(alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> PublicApiPrincipal:
    tenant_id = _tenant_from_key(x_api_key)
    set_tenant_context(db, tenant_id)
    key = (
        db.query(PublicApiKey)
        .filter(
            PublicApiKey.tenant_id == tenant_id,
            PublicApiKey.key_hash == _hash(x_api_key),
            PublicApiKey.is_active.is_(True),
        )
        .one_or_none()
    )
    now = datetime.now(timezone.utc)
    if not key or (key.expires_at and key.expires_at <= now):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    key.last_used_at = now
    db.commit()
    return PublicApiPrincipal(
        tenant_id=tenant_id,
        key_id=key.id,
        scopes=frozenset(json.loads(key.scopes_json or "[]")),
    )


def _tenant_from_key(raw_key: str) -> UUID:
    parts = raw_key.split("_", 3)
    if len(parts) != 4 or parts[:2] != ["voknap", "live"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    try:
        return UUID(hex=parts[2])
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key") from error


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()
