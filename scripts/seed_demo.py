from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.accounts.models import Membership, Tenant, User
from app.modules.activity.models import Activity
from app.modules.ai_agent.models import AgentAction, AgentMessage
from app.modules.connectors.models import ConnectorAccount, ConnectorSyncRun
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument, KnowledgeQuery
from app.modules.production.models import AuditLog, FeatureFlag, TenantPlan
from app.modules.sales.models import Company, Contact, Deal, Lead, Note, Pipeline, PipelineStage, Task


DEMO_TENANT_SLUG = "demo-sales-ai"
DEMO_USER_EMAIL = "demo@cmr.local"
DEMO_USER_PASSWORD = "password123"


def now() -> datetime:
    return datetime.now(timezone.utc)


def remove_existing_demo(db: Session) -> None:
    tenant = db.query(Tenant).filter(Tenant.slug == DEMO_TENANT_SLUG).one_or_none()
    user = db.query(User).filter(User.email == DEMO_USER_EMAIL).one_or_none()

    if tenant:
        tenant_id = tenant.id
        for model in (
            ConnectorSyncRun,
            ConnectorAccount,
            AgentAction,
            AgentMessage,
            KnowledgeQuery,
            KnowledgeChunk,
            KnowledgeDocument,
            AuditLog,
            FeatureFlag,
            TenantPlan,
            Activity,
            Note,
            Task,
            Deal,
            Lead,
            Contact,
            PipelineStage,
            Pipeline,
            Company,
            Membership,
        ):
            db.query(model).filter(model.tenant_id == tenant_id).delete(synchronize_session=False)
        db.delete(tenant)

    if user:
        db.delete(user)

    db.commit()


def create_pipeline(db: Session, tenant: Tenant) -> list[PipelineStage]:
    pipeline = Pipeline(tenant_id=tenant.id, name="Enterprise Sales")
    db.add(pipeline)
    db.flush()

    stages = []
    for index, name in enumerate(("New", "Discovery", "Proposal", "Negotiation", "Won")):
        stage = PipelineStage(tenant_id=tenant.id, pipeline_id=pipeline.id, name=name, sort_order=index)
        db.add(stage)
        stages.append(stage)
    db.flush()
    return stages


def create_company_pack(
    db: Session,
    tenant: Tenant,
    user: User,
    stages: list[PipelineStage],
    *,
    name: str,
    website: str,
    industry: str,
    description: str,
    contact_name: str,
    contact_email: str,
    contact_phone: str,
    deal_title: str,
    amount: int,
    stage_index: int,
    source: str,
    task_title: str,
    due_shift_days: int,
) -> None:
    company = Company(
        tenant_id=tenant.id,
        name=name,
        website=website,
        industry=industry,
        description=description,
        created_at=now() - timedelta(days=stage_index + 7),
    )
    db.add(company)
    db.flush()

    contact = Contact(
        tenant_id=tenant.id,
        company_id=company.id,
        name=contact_name,
        phone=contact_phone,
        email=contact_email,
        company_name=name,
        created_at=now() - timedelta(days=stage_index + 6),
    )
    db.add(contact)
    db.flush()

    lead = Lead(
        tenant_id=tenant.id,
        company_id=company.id,
        contact_id=contact.id,
        title=f"Запрос на внедрение CRM: {name}",
        source=source,
        status="qualified",
        created_at=now() - timedelta(days=stage_index + 5),
    )
    db.add(lead)
    db.flush()

    deal = Deal(
        tenant_id=tenant.id,
        company_id=company.id,
        lead_id=lead.id,
        stage_id=stages[stage_index].id,
        title=deal_title,
        amount=amount,
        status="won" if stages[stage_index].name == "Won" else "open",
        created_at=now() - timedelta(days=stage_index + 4),
    )
    db.add(deal)
    db.flush()

    db.add(
        Task(
            tenant_id=tenant.id,
            company_id=company.id,
            assigned_to_id=user.id,
            deal_id=deal.id,
            title=task_title,
            description="Следующее действие создано для проверки рабочего интерфейса.",
            due_at=now() + timedelta(days=due_shift_days),
            done_at=None if due_shift_days >= 0 else now() - timedelta(hours=8),
            created_at=now() - timedelta(days=2),
        )
    )
    db.add(
        Note(
            tenant_id=tenant.id,
            company_id=company.id,
            author_id=user.id,
            deal_id=deal.id,
            text=f"Клиент {name} подтвердил интерес. Нужно держать фокус на следующем шаге.",
            created_at=now() - timedelta(days=1, hours=stage_index),
        )
    )

    activity_rows = [
        ("CALL", "Call completed", "Обсудили текущий процесс продаж и узкие места.", -3),
        ("MEETING", "Discovery meeting", "Зафиксировали участников, сроки и критерии успеха.", -2),
        ("AI_SUMMARY_UPDATED", "AI generated summary", "AI обновил краткую сводку компании.", -1),
        ("DEAL_STAGE_CHANGED", f"Stage moved to {stages[stage_index].name}", "Сделка перешла на текущий этап.", 0),
    ]
    for activity_type, title, text, shift in activity_rows:
        db.add(
            Activity(
                tenant_id=tenant.id,
                company_id=company.id,
                contact_id=contact.id,
                deal_id=deal.id,
                type=activity_type,
                title=title,
                description=text,
                created_by=user.id,
                metadata_json=json.dumps({"demo": True, "company": name}),
                created_at=now() + timedelta(days=shift, hours=stage_index),
            )
        )


def create_knowledge(db: Session, tenant: Tenant, user: User) -> None:
    documents = [
        (
            "Sales Playbook: AI-first CRM",
            "Первый контакт: ответить в течение 15 минут, определить роль покупателя, собрать контекст компании, создать next action и activity.",
        ),
        (
            "Enterprise Qualification",
            "Квалификация B2B сделки: бюджет, процесс принятия решения, интеграции, сроки внедрения, риски безопасности, владелец процесса.",
        ),
        (
            "Objection Handling",
            "Типовые возражения: уже есть CRM, нет времени на внедрение, нужна интеграция с телефонией, нужна миграция данных, нужен пилот.",
        ),
    ]
    for title, text in documents:
        document = KnowledgeDocument(tenant_id=tenant.id, title=title, source_type="text", status="ready")
        db.add(document)
        db.flush()
        db.add(
            KnowledgeChunk(
                tenant_id=tenant.id,
                document_id=document.id,
                chunk_index=0,
                text=text,
                embedding_json=json.dumps([0.12, 0.24, 0.48, 0.96]),
                token_estimate=len(text.split()),
            )
        )

    db.add(
        KnowledgeQuery(
            tenant_id=tenant.id,
            user_id=user.id,
            question="Что делать после новой заявки?",
            answer="Создать компанию, контакт, сделку, next action и активность в timeline.",
        )
    )


def create_platform_data(db: Session, tenant: Tenant, user: User) -> None:
    account = ConnectorAccount(
        tenant_id=tenant.id,
        connector_code="csv",
        title="CSV import/export",
        status="connected",
        credentials_json="{}",
        settings_json=json.dumps({"delimiter": ","}),
        last_sync_at=now() - timedelta(hours=2),
    )
    db.add(account)
    db.flush()

    db.add(
        ConnectorSyncRun(
            tenant_id=tenant.id,
            account_id=account.id,
            direction="import",
            status="success",
            created_count=12,
            updated_count=4,
            failed_count=0,
            message="Demo import completed",
        )
    )

    for role, content in (
        ("user", "Дай сводку по приоритетным сделкам"),
        ("assistant", "В фокусе Альфа Ритейл, СибТех и Nova Logistics. У каждой есть следующий шаг и свежий timeline."),
    ):
        db.add(AgentMessage(tenant_id=tenant.id, user_id=user.id, role=role, content=content))

    db.add(
        AgentAction(
            tenant_id=tenant.id,
            user_id=user.id,
            action_type="create_task",
            status="pending",
            payload_json=json.dumps({"title": "Подготовить executive summary", "demo": True}),
            result_json=None,
        )
    )

    for code, title, enabled in (
        ("ai_agent", "AI Agent", True),
        ("connectors", "External Connectors", True),
        ("analytics", "Analytics", True),
    ):
        db.add(FeatureFlag(tenant_id=tenant.id, code=code, title=title, enabled=enabled))

    db.add(TenantPlan(tenant_id=tenant.id, plan_code="demo", users_limit=25, leads_limit=5000, documents_limit=500, ai_requests_limit=50000))
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            user_id=user.id,
            action="demo_seed_created",
            entity_type="tenant",
            entity_id=str(tenant.id),
            payload_json=json.dumps({"source": "scripts/seed_demo.py"}),
        )
    )


def seed() -> None:
    db = SessionLocal()
    try:
        remove_existing_demo(db)

        tenant = Tenant(name="Demo AI Sales OS", slug=DEMO_TENANT_SLUG, is_active=True)
        user = User(email=DEMO_USER_EMAIL, full_name="Demo Sales Owner", password_hash=hash_password(DEMO_USER_PASSWORD), is_active=True)
        db.add_all([tenant, user])
        db.flush()
        db.add(Membership(tenant_id=tenant.id, user_id=user.id, role="owner"))

        stages = create_pipeline(db, tenant)
        for spec in (
            ("Альфа Ритейл", "https://alpha-retail.example", "Retail", "Федеральная розничная сеть. Ищет AI-first CRM для B2B отдела продаж.", "Мария Волкова", "m.volkova@alpha-retail.example", "+7 999 100-10-01", "CRM rollout на 120 менеджеров", 4_800_000, 3, "partner", "Отправить финальное КП", 1),
            ("СибТех Инжиниринг", "https://sibtech.example", "Industrial", "Инжиниринговая компания. Нужна миграция сделок, задач и истории коммуникаций.", "Игорь Соколов", "i.sokolov@sibtech.example", "+7 999 100-10-02", "Миграция CRM и внедрение RAG", 3_200_000, 2, "site", "Согласовать пилотный контур", 3),
            ("Nova Logistics", "https://nova-logistics.example", "Logistics", "Логистический оператор в СНГ. Нужна единая timeline по клиентам и филиалам.", "Алена Каримова", "a.karimova@nova-logistics.example", "+7 999 100-10-03", "AI workspace для коммерческого блока", 2_650_000, 1, "conference", "Провести discovery call", -1),
            ("FinBridge", "https://finbridge.example", "Fintech", "Финтех-платформа. Интерес к безопасному AI агенту и журналу действий.", "Дмитрий Орлов", "d.orlov@finbridge.example", "+7 999 100-10-04", "AI Agent и compliance timeline", 5_100_000, 0, "referral", "Подготовить security brief", 2),
            ("MedCloud СНГ", "https://medcloud.example", "HealthTech", "SaaS для клиник. Смотрит CRM для партнерских продаж и базы знаний.", "Екатерина Лазарева", "e.lazareva@medcloud.example", "+7 999 100-10-05", "CRM для партнерской сети", 1_900_000, 4, "webinar", "Передать в onboarding", 5),
        ):
            create_company_pack(
                db,
                tenant,
                user,
                stages,
                name=spec[0],
                website=spec[1],
                industry=spec[2],
                description=spec[3],
                contact_name=spec[4],
                contact_email=spec[5],
                contact_phone=spec[6],
                deal_title=spec[7],
                amount=spec[8],
                stage_index=spec[9],
                source=spec[10],
                task_title=spec[11],
                due_shift_days=spec[12],
            )

        create_knowledge(db, tenant, user)
        create_platform_data(db, tenant, user)
        db.commit()

        print("Demo data created")
        print(f"Tenant: {tenant.name} / {tenant.slug}")
        print(f"Login: {DEMO_USER_EMAIL}")
        print(f"Password: {DEMO_USER_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
