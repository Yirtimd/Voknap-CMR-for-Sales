import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

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
    ConnectorDefinition("email", "Email", "Заготовка для входящих писем и исходящих сообщений.", "planned"),
    ConnectorDefinition("telegram", "Telegram", "Заготовка для лидов из Telegram.", "planned"),
    ConnectorDefinition("bitrix24", "Bitrix24", "Заготовка для импорта лидов из Bitrix24.", "planned"),
    ConnectorDefinition("amocrm", "amoCRM", "Заготовка для импорта сделок из amoCRM.", "planned"),
    ConnectorDefinition("onec", "1C", "Заготовка для клиентов, товаров и счетов из 1C.", "planned"),
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

        account = ConnectorAccount(
            tenant_id=tenant_id,
            connector_code=connector_code,
            title=title,
            credentials_json=json.dumps(credentials),
            settings_json=json.dumps(settings),
            status="connected" if connector_code == "csv" else "planned",
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
        return self._save_run(tenant_id, account_id, "inbound", "success", created, 0, failed, "CSV import completed")

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
    ) -> ConnectorSyncRun:
        run = ConnectorSyncRun(
            tenant_id=tenant_id,
            account_id=account_id,
            direction=direction,
            status=status,
            created_count=created,
            updated_count=updated,
            failed_count=failed,
            message=message,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run
