import base64
import csv
import hashlib
import imaplib
import io
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email import message_from_bytes, policy
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.communication.models import CommunicationEvent
from app.modules.communication.schemas import CommunicationEventCreate
from app.modules.communication.service import CommunicationService
from app.modules.connectors.models import ConnectorAccount, ConnectorSyncRun
from app.modules.sales.models import Company, Contact, Lead


@dataclass(frozen=True)
class ConnectorDefinition:
    code: str
    title: str
    description: str
    status: str


CONNECTORS = [
    ConnectorDefinition("csv", "CSV import/export", "Импорт и экспорт лидов и контактов через CSV.", "ready"),
    ConnectorDefinition("email", "Email (IMAP)", "Реальная загрузка входящих писем по IMAP и привязка к CRM.", "ready"),
    ConnectorDefinition("calendar", "Calendar", "Импорт событий календаря через API пока не подключён.", "placeholder"),
    ConnectorDefinition("telephony", "Telephony", "Placeholder для звонков, записей и call activity.", "placeholder"),
    ConnectorDefinition("bitrix24", "Bitrix24", "Миграция компаний, контактов и лидов из Bitrix24.", "ready"),
    ConnectorDefinition("amocrm", "amoCRM", "Миграция компаний, контактов и сделок из amoCRM.", "ready"),
    ConnectorDefinition("onec", "1C", "Placeholder для клиентов, товаров и счетов из 1C.", "placeholder"),
]


class ConnectorService:
    def __init__(self, db: Session):
        self.db = db

    def definitions(self) -> list[ConnectorDefinition]:
        return CONNECTORS

    def create_account(
        self,
        tenant_id: UUID,
        connector_code: str,
        title: str,
        credentials: dict,
        settings: dict,
    ) -> ConnectorAccount:
        if connector_code not in {connector.code for connector in CONNECTORS}:
            raise ValueError("Unknown connector")

        if connector_code == "email":
            if settings.secret_key == "change-me-in-production" or len(settings.secret_key) < 32:
                raise ValueError("Set a unique SECRET_KEY of at least 32 characters before connecting email")
            self._validate_email_config(credentials, settings)
            self._test_imap_connection(credentials, settings)

        account = ConnectorAccount(
            tenant_id=tenant_id,
            connector_code=connector_code,
            title=title,
            credentials_json=self._encrypt_credentials(credentials),
            credentials_encrypted=True,
            settings_json=json.dumps(settings),
            status="connected" if connector_code in {"csv", "email", "bitrix24", "amocrm"} else "placeholder",
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def list_accounts(self, tenant_id: UUID) -> list[ConnectorAccount]:
        return (
            self.db.query(ConnectorAccount)
            .filter(ConnectorAccount.tenant_id == tenant_id)
            .order_by(ConnectorAccount.created_at.desc())
            .all()
        )

    def import_csv_leads(self, tenant_id: UUID, account_id: UUID, csv_text: str) -> ConnectorSyncRun:
        account = self._get_account(tenant_id, account_id)
        if account is None or account.connector_code != "csv":
            return self._save_run(tenant_id, account_id, "inbound", "failed", 0, 0, 1, "CSV connector not found")

        reader = csv.DictReader(io.StringIO(csv_text))
        created = 0
        failed = 0
        for row in reader:
            try:
                contact = Contact(
                    tenant_id=tenant_id,
                    company_id=self._get_or_create_company(
                        tenant_id,
                        (row.get("company_name") or "Imported company").strip() or "Imported company",
                    ).id,
                    name=(row.get("name") or row.get("contact_name") or "Без имени").strip(),
                    phone=(row.get("phone") or "").strip() or None,
                    email=(row.get("email") or "").strip() or None,
                    company_name=(row.get("company_name") or "").strip() or None,
                )
                self.db.add(contact)
                self.db.flush()

                lead = Lead(
                    tenant_id=tenant_id,
                    company_id=contact.company_id,
                    contact_id=contact.id,
                    title=(row.get("lead_title") or row.get("title") or f"Лид: {contact.name}").strip(),
                    source=(row.get("source") or "csv").strip(),
                    status="new",
                )
                self.db.add(lead)
                created += 1
            except Exception:
                failed += 1

        account.last_sync_at = datetime.now(timezone.utc)
        return self._save_run(tenant_id, account_id, "inbound", "success", created, 0, failed, "CSV import completed", job_type="csv_import")

    def sync_account(self, tenant_id: UUID, account_id: UUID, payload: dict | None = None) -> ConnectorSyncRun:
        account = self._get_account(tenant_id, account_id)
        if account is None:
            return self._save_run(
                tenant_id,
                account_id,
                "inbound",
                "failed",
                0,
                0,
                1,
                "Connector account not found",
                error_code="account_not_found",
            )

        started_at = datetime.now(timezone.utc)
        try:
            if account.connector_code == "email":
                run = self._sync_email(tenant_id, account, payload or {})
            elif account.connector_code == "calendar":
                run = self._sync_calendar(tenant_id, account, payload or {})
            elif account.connector_code == "telephony":
                run = self._placeholder_run(tenant_id, account, "telephony_sync", "Telephony connector placeholder is ready")
            elif account.connector_code in {"amocrm", "bitrix24"}:
                run = self._sync_crm_migration(tenant_id, account, payload or {})
            else:
                run = self._placeholder_run(tenant_id, account, f"{account.connector_code}_sync", "Connector sync placeholder is ready")
            run.started_at = started_at
            run.finished_at = datetime.now(timezone.utc)
            account.last_sync_at = run.finished_at
            self.db.commit()
            self.db.refresh(run)
            return run
        except Exception as error:
            return self._save_run(
                tenant_id,
                account.id,
                "inbound",
                "failed",
                0,
                0,
                1,
                str(error),
                job_type=f"{account.connector_code}_sync",
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
                error_code=error.__class__.__name__,
                error_details={"connector_code": account.connector_code},
            )

    def retry_run(self, tenant_id: UUID, run_id: UUID) -> ConnectorSyncRun | None:
        run = (
            self.db.query(ConnectorSyncRun)
            .filter(ConnectorSyncRun.id == run_id, ConnectorSyncRun.tenant_id == tenant_id)
            .one_or_none()
        )
        if run is None:
            return None
        if run.status not in {"failed", "retry_scheduled"}:
            return run
        if run.attempt >= run.max_attempts:
            run.status = "failed"
            run.message = "Max retry attempts reached"
            self.db.commit()
            self.db.refresh(run)
            return run

        retry = self.sync_account(tenant_id, run.account_id, payload={"retry_of": str(run.id)})
        retry.attempt = run.attempt + 1
        retry.max_attempts = run.max_attempts
        self.db.commit()
        self.db.refresh(retry)
        return retry

    def export_csv_leads(self, tenant_id: UUID) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["lead_id", "lead_title", "status", "source", "contact_id", "name", "phone", "email", "company_name"])

        rows = (
            self.db.query(Lead, Contact)
            .outerjoin(Contact, Contact.id == Lead.contact_id)
            .filter(Lead.tenant_id == tenant_id)
            .order_by(Lead.created_at.desc())
            .all()
        )
        for lead, contact in rows:
            writer.writerow(
                [
                    lead.id,
                    lead.title,
                    lead.status,
                    lead.source or "",
                    contact.id if contact else "",
                    contact.name if contact else "",
                    contact.phone if contact else "",
                    contact.email if contact else "",
                    contact.company_name if contact else "",
                ]
            )

        return output.getvalue()

    def _get_or_create_company(self, tenant_id: UUID, name: str) -> Company:
        company = (
            self.db.query(Company)
            .filter(Company.tenant_id == tenant_id, Company.name == name)
            .one_or_none()
        )
        if company:
            return company
        company = Company(tenant_id=tenant_id, name=name)
        self.db.add(company)
        self.db.flush()
        return company

    def list_runs(self, tenant_id: UUID) -> list[ConnectorSyncRun]:
        return (
            self.db.query(ConnectorSyncRun)
            .filter(ConnectorSyncRun.tenant_id == tenant_id)
            .order_by(ConnectorSyncRun.created_at.desc())
            .limit(50)
            .all()
        )

    def _sync_email(self, tenant_id: UUID, account: ConnectorAccount, payload: dict) -> ConnectorSyncRun:
        credentials = self._decrypt_credentials(account.credentials_json)
        account_settings = json.loads(account.settings_json or "{}")
        limit = min(max(int(payload.get("limit") or account_settings.get("sync_limit") or 100), 1), 500)
        messages, last_uid = self._fetch_imap_messages(
            credentials=credentials,
            settings=account_settings,
            after_uid=int(account.sync_cursor or 0),
            limit=limit,
        )
        created = 0
        for item in messages:
            before = (
                self.db.query(CommunicationEvent)
                .filter(
                    CommunicationEvent.tenant_id == tenant_id,
                    CommunicationEvent.channel == "email",
                    CommunicationEvent.external_id == item["external_id"],
                )
                .one_or_none()
            )
            CommunicationService(self.db).create(
                tenant_id=tenant_id,
                created_by=None,
                payload=CommunicationEventCreate(
                    channel="email",
                    direction="inbound",
                    external_id=item["external_id"],
                    sender=item.get("sender"),
                    recipient=item.get("recipient"),
                    subject=item.get("subject") or "Без темы",
                    body=item.get("body"),
                    occurred_at=item.get("occurred_at"),
                    connector_account_id=account.id,
                    metadata={
                        "connector_account_id": str(account.id),
                        "imap_uid": item["uid"],
                        "message_id": item.get("message_id"),
                    },
                ),
            )
            if before is None:
                created += 1
        if last_uid is not None:
            account.sync_cursor = str(last_uid)
        return self._save_run(
            tenant_id,
            account.id,
            "inbound",
            "success",
            created,
            0,
            0,
            f"Email sync completed: {created} new messages",
            job_type="email_sync",
        )

    def _validate_email_config(self, credentials: dict, settings: dict) -> None:
        missing = [key for key in ("username", "password") if not credentials.get(key)]
        if not settings.get("host"):
            missing.append("host")
        if missing:
            raise ValueError(f"Email connector requires: {', '.join(missing)}")

    def _test_imap_connection(self, credentials: dict, settings: dict) -> None:
        client = self._imap_connect(credentials, settings)
        try:
            folder = str(settings.get("folder") or "INBOX")
            status, _ = client.select(folder, readonly=True)
            if status != "OK":
                raise ValueError(f"IMAP folder is unavailable: {folder}")
        finally:
            try:
                client.logout()
            except imaplib.IMAP4.error:
                pass

    def _imap_connect(self, credentials: dict, settings: dict) -> imaplib.IMAP4:
        self._validate_email_config(credentials, settings)
        host = str(settings["host"])
        port = int(settings.get("port") or (993 if settings.get("use_ssl", True) else 143))
        timeout = int(settings.get("timeout_seconds") or 15)
        try:
            if settings.get("use_ssl", True):
                client: imaplib.IMAP4 = imaplib.IMAP4_SSL(host, port, timeout=timeout)
            else:
                client = imaplib.IMAP4(host, port, timeout=timeout)
                if settings.get("starttls", True):
                    client.starttls()
            client.login(str(credentials["username"]), str(credentials["password"]))
            return client
        except (OSError, imaplib.IMAP4.error) as error:
            raise ValueError(f"IMAP connection failed: {error}") from error

    def _fetch_imap_messages(
        self,
        credentials: dict,
        settings: dict,
        after_uid: int,
        limit: int,
    ) -> tuple[list[dict], int | None]:
        client = self._imap_connect(credentials, settings)
        folder = str(settings.get("folder") or "INBOX")
        messages: list[dict] = []
        last_uid: int | None = None
        try:
            status, _ = client.select(folder, readonly=True)
            if status != "OK":
                raise ValueError(f"IMAP folder is unavailable: {folder}")
            status, result = client.uid("search", None, f"UID {after_uid + 1}:*")
            if status != "OK":
                raise ValueError("IMAP message search failed")
            uids = [int(value) for value in (result[0] or b"").split() if value]
            for uid in uids[:limit]:
                status, rows = client.uid("fetch", str(uid), "(RFC822)")
                if status != "OK":
                    continue
                raw = next((row[1] for row in rows if isinstance(row, tuple) and isinstance(row[1], bytes)), None)
                if raw is None:
                    continue
                message = message_from_bytes(raw, policy=policy.default)
                message_id = str(message.get("Message-ID") or "").strip() or None
                messages.append(
                    {
                        "uid": uid,
                        "external_id": f"{account_identity(settings, credentials)}:{folder}:{uid}",
                        "message_id": message_id,
                        "sender": self._decode_header_value(message.get("From")),
                        "recipient": self._decode_header_value(message.get("To")),
                        "subject": self._decode_header_value(message.get("Subject")) or "Без темы",
                        "body": self._message_body(message),
                        "occurred_at": self._message_date(message),
                    }
                )
                last_uid = uid
            if uids and last_uid is None:
                last_uid = uids[min(len(uids), limit) - 1]
            return messages, last_uid
        finally:
            try:
                client.logout()
            except imaplib.IMAP4.error:
                pass

    def _decode_header_value(self, value: str | None) -> str | None:
        if not value:
            return None
        parts = []
        for part, encoding in decode_header(value):
            if isinstance(part, bytes):
                parts.append(part.decode(encoding or "utf-8", errors="replace"))
            else:
                parts.append(part)
        return "".join(parts).strip() or None

    def _message_body(self, message: Message) -> str | None:
        plain: list[str] = []
        html: list[str] = []
        parts = message.walk() if message.is_multipart() else [message]
        for part in parts:
            if part.get_content_disposition() == "attachment":
                continue
            content_type = part.get_content_type()
            if content_type not in {"text/plain", "text/html"}:
                continue
            try:
                content = part.get_content()
            except (LookupError, UnicodeDecodeError):
                payload = part.get_payload(decode=True) or b""
                content = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            if content_type == "text/plain":
                plain.append(str(content))
            else:
                html.append(str(content))
        body = "\n".join(plain).strip()
        if not body and html:
            body = re.sub(r"<[^>]+>", " ", "\n".join(html))
            body = re.sub(r"\s+", " ", body).strip()
        return body or None

    def _message_date(self, message: Message) -> datetime:
        value = message.get("Date")
        if value:
            try:
                parsed = parsedate_to_datetime(value)
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed
            except (TypeError, ValueError, OverflowError):
                pass
        return datetime.now(timezone.utc)

    def _sync_calendar(self, tenant_id: UUID, account: ConnectorAccount, payload: dict) -> ConnectorSyncRun:
        events = payload.get("events") or json.loads(account.settings_json or "{}").get("events") or []
        created = 0
        for item in events:
            company = self._get_or_create_company(tenant_id, item.get("company_name") or "Calendar company")
            CommunicationService(self.db).create(
                tenant_id=tenant_id,
                created_by=None,
                payload=CommunicationEventCreate(
                    channel="calendar",
                    direction="inbound",
                    external_id=item.get("id"),
                    sender=item.get("organizer"),
                    recipient=item.get("attendee"),
                    subject=item.get("title") or "Meeting scheduled",
                    body=item.get("description"),
                    company_id=company.id,
                    connector_account_id=account.id,
                    metadata={"connector_account_id": str(account.id), "starts_at": item.get("starts_at")},
                ),
            )
            created += 1
        return self._save_run(tenant_id, account.id, "inbound", "success", created, 0, 0, "Calendar sync completed", job_type="calendar_sync")

    def _sync_crm_migration(self, tenant_id: UUID, account: ConnectorAccount, payload: dict) -> ConnectorSyncRun:
        rows = payload.get("records") or json.loads(account.settings_json or "{}").get("records") or []
        created = 0
        updated = 0
        failed = 0
        for item in rows:
            try:
                company = self._get_or_create_company(tenant_id, item.get("company_name") or item.get("company") or "Imported CRM company")
                contact_name = item.get("contact_name") or item.get("name")
                if contact_name:
                    existing_contact = (
                        self.db.query(Contact)
                        .filter(Contact.tenant_id == tenant_id, Contact.company_id == company.id, Contact.email == item.get("email"))
                        .one_or_none()
                    )
                    if existing_contact:
                        existing_contact.phone = item.get("phone") or existing_contact.phone
                        updated += 1
                    else:
                        self.db.add(Contact(
                            tenant_id=tenant_id,
                            company_id=company.id,
                            name=contact_name,
                            phone=item.get("phone"),
                            email=item.get("email"),
                            company_name=company.name,
                        ))
                        created += 1
                lead_title = item.get("lead_title") or item.get("deal_title")
                if lead_title:
                    self.db.add(Lead(
                        tenant_id=tenant_id,
                        company_id=company.id,
                        title=lead_title,
                        source=account.connector_code,
                        status="new",
                    ))
                    created += 1
            except Exception:
                failed += 1
        return self._save_run(
            tenant_id,
            account.id,
            "inbound",
            "success" if failed == 0 else "partial",
            created,
            updated,
            failed,
            f"{account.connector_code} migration completed",
            job_type=f"{account.connector_code}_migration",
        )

    def _placeholder_run(self, tenant_id: UUID, account: ConnectorAccount, job_type: str, message: str) -> ConnectorSyncRun:
        return self._save_run(tenant_id, account.id, "inbound", "queued", 0, 0, 0, message, job_type=job_type)

    def _get_account(self, tenant_id: UUID, account_id: UUID) -> ConnectorAccount | None:
        return (
            self.db.query(ConnectorAccount)
            .filter(ConnectorAccount.id == account_id, ConnectorAccount.tenant_id == tenant_id)
            .one_or_none()
        )

    def _save_run(
        self,
        tenant_id: UUID,
        account_id: UUID,
        direction: str,
        status: str,
        created: int,
        updated: int,
        failed: int,
        message: str,
        job_type: str = "sync",
        attempt: int = 1,
        max_attempts: int = 3,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        error_code: str | None = None,
        error_details: dict | None = None,
    ) -> ConnectorSyncRun:
        next_retry_at = None
        if status == "failed" and attempt < max_attempts:
            next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=attempt * 5)
            status = "retry_scheduled"
        run = ConnectorSyncRun(
            tenant_id=tenant_id,
            account_id=account_id,
            direction=direction,
            status=status,
            job_type=job_type,
            attempt=attempt,
            max_attempts=max_attempts,
            next_retry_at=next_retry_at,
            started_at=started_at,
            finished_at=finished_at,
            created_count=created,
            updated_count=updated,
            failed_count=failed,
            message=message,
            error_code=error_code,
            error_details_json=json.dumps(error_details or {}),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def _encrypt_credentials(self, credentials: dict) -> str:
        payload = json.dumps(credentials).encode("utf-8")
        return self._fernet().encrypt(payload).decode("ascii")

    def _decrypt_credentials(self, value: str) -> dict:
        try:
            decrypted = self._fernet().decrypt(value.encode("ascii"))
            return json.loads(decrypted.decode("utf-8"))
        except InvalidToken:
            # Compatibility with accounts created before authenticated encryption.
            key = settings.secret_key.encode("utf-8")
            data = base64.urlsafe_b64decode(value.encode("ascii"))
            decrypted = bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data))
            return json.loads(decrypted.decode("utf-8"))

    def _fernet(self) -> Fernet:
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode("utf-8")).digest())
        return Fernet(key)


def account_identity(settings: dict, credentials: dict) -> str:
    raw = f"{settings.get('host', '')}:{credentials.get('username', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
