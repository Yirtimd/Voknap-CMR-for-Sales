from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.connectors.models import ConnectorAccount
from app.modules.connectors.providers import (
    exchange_authorization_code,
    google_authorization_url,
    microsoft_authorization_url,
)
from app.modules.connectors.service import ConnectorService


ALGORITHM = "HS256"


def create_authorization_url(account: ConnectorAccount, user_id: UUID) -> str:
    if settings.secret_key == "change-me-in-production" or len(settings.secret_key) < 32:
        raise ValueError("Set a unique SECRET_KEY of at least 32 characters before OAuth")
    payload = {
        "purpose": "connector_oauth",
        "tenant_id": str(account.tenant_id),
        "account_id": str(account.id),
        "user_id": str(user_id),
        "provider": account.connector_code,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    state = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    if account.connector_code == "google_calendar":
        return google_authorization_url(state)
    if account.connector_code == "microsoft_calendar":
        return microsoft_authorization_url(state)
    raise ValueError("Account does not support OAuth")


def complete_authorization(db: Session, provider: str, code: str, state: str) -> ConnectorAccount:
    try:
        payload = jwt.decode(state, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("purpose") != "connector_oauth" or payload.get("provider") != provider:
            raise ValueError("OAuth state does not match provider")
        tenant_id = UUID(payload["tenant_id"])
        account_id = UUID(payload["account_id"])
    except (JWTError, KeyError, ValueError) as error:
        raise ValueError("OAuth state is invalid or expired") from error

    from app.core.database import set_tenant_context

    set_tenant_context(db, tenant_id)
    account = (
        db.query(ConnectorAccount)
        .filter(
            ConnectorAccount.tenant_id == tenant_id,
            ConnectorAccount.id == account_id,
            ConnectorAccount.connector_code == provider,
        )
        .one_or_none()
    )
    if not account:
        raise ValueError("OAuth connector account not found")
    credentials = exchange_authorization_code(provider, code)
    account.credentials_json = ConnectorService(db)._encrypt_credentials(credentials)
    account.credentials_encrypted = True
    account.status = "connected"
    db.commit()
    db.refresh(account)
    return account
