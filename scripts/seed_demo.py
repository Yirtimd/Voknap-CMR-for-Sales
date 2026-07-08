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
from app.modules.communication.models import CommunicationEvent
from app.modules.connectors.models import ConnectorAccount, ConnectorSyncRun
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument, KnowledgeQuery
from app.modules.knowledge.service import EmbeddingService
from app.modules.production.models import AuditLog, FeatureFlag, TenantPlan
from app.modules.sales.models import (
    Company,
    CompanyFile,
    Contact,
    CustomerInsight,
    Deal,
    Lead,
    NextAction,
    Note,
    Pipeline,
    PipelineStage,
    Task,
)


DEMO_TENANT_SLUG = "demo-sales-ai"
DEMO_USER_EMAIL = "demo@cmrsales.app"
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
            CommunicationEvent,
            AgentAction,
            AgentMessage,
            KnowledgeQuery,
            KnowledgeChunk,
            KnowledgeDocument,
            AuditLog,
            FeatureFlag,
            TenantPlan,
            CompanyFile,
            CustomerInsight,
            NextAction,
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
        status="active",
        company_type="B2B",
        health_score=min(96, 72 + stage_index * 4),
        client_since=now() - timedelta(days=stage_index + 30),
        owner_id=user.id,
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
        role="CEO" if stage_index % 2 == 0 else "Менеджер",
        can_call=True,
        can_email=True,
        can_open_more=True,
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
        probability=min(95, 35 + stage_index * 15),
        expected_close_date=now() + timedelta(days=14 + stage_index * 7),
        expected_next_event="Ожидаем: ответа клиента",
        next_step=task_title,
        risk_level="high" if due_shift_days < 0 else "medium",
        forecast_category="commit" if stage_index >= 3 else "pipeline",
        owner_id=user.id,
        created_at=now() - timedelta(days=stage_index + 4),
    )
    db.add(deal)
    db.flush()

    next_action = NextAction(
        tenant_id=tenant.id,
        company_id=company.id,
        deal_id=deal.id,
        contact_id=contact.id,
        assigned_to_id=user.id,
        title=task_title,
        description="Главное следующее действие для company workspace.",
        source="ai" if stage_index % 2 == 0 else "manual",
        status="open",
        priority="high" if due_shift_days <= 1 else "normal",
        due_at=now() + timedelta(days=due_shift_days),
        created_at=now() - timedelta(days=1),
    )
    db.add(next_action)
    db.flush()
    company.next_action_id = next_action.id
    deal.next_action_id = next_action.id

    db.add(
        Task(
            tenant_id=tenant.id,
            company_id=company.id,
            assigned_to_id=user.id,
            deal_id=deal.id,
            title=task_title,
            description="Следующее действие создано для проверки рабочего интерфейса.",
            status="open" if due_shift_days >= 0 else "done",
            priority="high" if due_shift_days <= 1 else "normal",
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

    db.add(
        CustomerInsight(
            tenant_id=tenant.id,
            company_id=company.id,
            health_score=min(96, 72 + stage_index * 4),
            health_label="Хороший",
            health_trend="up" if stage_index != 0 else "flat",
            risk_level="high" if due_shift_days < 0 else "medium",
            success_chance=min(92, 52 + stage_index * 8),
            success_chance_delta=4 - stage_index,
            ai_recommendations_json=json.dumps(
                [
                    {
                        "type": "warning" if due_shift_days < 0 else "info",
                        "title": "Контроль следующего шага",
                        "description": task_title,
                    },
                    {
                        "type": "success",
                        "title": "Сильный сигнал",
                        "description": f"Сделка на этапе {stages[stage_index].name}",
                    },
                ],
                ensure_ascii=False,
            ),
            updated_at=now() - timedelta(hours=2),
        )
    )

    for index, (file_name, file_type, file_size) in enumerate(
        (
            (f"КП_{name.replace(' ', '_')}.pdf", "PDF", 2_400_000 + stage_index * 110_000),
            (f"Discovery_{name.replace(' ', '_')}.xlsx", "XLSX", 1_100_000 + stage_index * 90_000),
        )
    ):
        file = CompanyFile(
            tenant_id=tenant.id,
            company_id=company.id,
            deal_id=deal.id,
            contact_id=contact.id,
            uploaded_by_id=user.id,
            name=file_name,
            file_type=file_type,
            mime_type="application/pdf" if file_type == "PDF" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_size=file_size,
            storage_key=f"demo/{company.id}/{file_name}",
            download_url=f"/demo-files/{company.id}/{index}",
            created_at=now() - timedelta(days=index + 1),
        )
        db.add(file)
        db.flush()
        if index == 0:
            add_knowledge_document(
                db,
                tenant,
                title=f"Proposal knowledge: {name}",
                text=(
                    f"Proposal for {name}. Deal: {deal.title}. Amount: {amount}. "
                    f"Next action: {task_title}. Risk level: {deal.risk_level}. "
                    "This document is scoped to company and deal context."
                ),
                source_type="proposal",
                company_id=company.id,
                deal_id=deal.id,
                file_id=file.id,
                visibility="company",
            )

    activity_rows = [
        ("CALL", "Call", "Call completed", "Обсудили текущий процесс продаж и узкие места.", -3),
        ("MEETING", "Meeting", "Discovery meeting", "Зафиксировали участников, сроки и критерии успеха.", -2),
        ("AI_SUMMARY_UPDATED", "AI", "AI generated summary", "AI обновил краткую сводку компании.", -1),
        ("DEAL_STAGE_CHANGED", "CRM", f"Stage moved to {stages[stage_index].name}", "Сделка перешла на текущий этап.", 0),
    ]
    for activity_type, channel, title, text, shift in activity_rows:
        db.add(
            Activity(
                tenant_id=tenant.id,
                company_id=company.id,
                contact_id=contact.id,
                deal_id=deal.id,
                type=activity_type,
                channel=channel,
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
        add_knowledge_document(db, tenant, title=title, text=text, source_type="text", visibility="global")

    db.add(
        KnowledgeQuery(
            tenant_id=tenant.id,
            user_id=user.id,
            question="Что делать после новой заявки?",
            answer="Создать компанию, контакт, сделку, next action и активность в timeline.",
        )
    )


def add_knowledge_document(
    db: Session,
    tenant: Tenant,
    *,
    title: str,
    text: str,
    source_type: str,
    visibility: str,
    company_id=None,
    deal_id=None,
    file_id=None,
) -> KnowledgeDocument:
    document = KnowledgeDocument(
        tenant_id=tenant.id,
        company_id=company_id,
        deal_id=deal_id,
        file_id=file_id,
        title=title,
        source_type=source_type,
        visibility=visibility,
        status="ready",
    )
    db.add(document)
    db.flush()
    embedding = EmbeddingService()._local_embed(text)
    db.add(
        KnowledgeChunk(
            tenant_id=tenant.id,
            document_id=document.id,
            chunk_index=0,
            text=text,
            embedding_json=json.dumps(embedding),
            token_estimate=len(text.split()),
        )
    )
    return document


def create_platform_data(db: Session, tenant: Tenant, user: User) -> None:
    account = ConnectorAccount(
        tenant_id=tenant.id,
        connector_code="csv",
        title="CSV import/export",
        status="connected",
        credentials_json="{}",
        credentials_encrypted=True,
        settings_json=json.dumps({"delimiter": ","}),
        sync_cursor="demo-csv-cursor",
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
            job_type="csv_import",
            attempt=1,
            max_attempts=3,
            started_at=now() - timedelta(hours=2, minutes=1),
            finished_at=now() - timedelta(hours=2),
            created_count=12,
            updated_count=4,
            failed_count=0,
            message="Demo import completed",
            error_details_json="{}",
        )
    )
    for code, title, status in (
        ("email", "Demo Email inbox", "connected"),
        ("calendar", "Demo Calendar", "connected"),
        ("telephony", "Demo Telephony", "placeholder"),
        ("amocrm", "Demo amoCRM migration", "connected"),
        ("bitrix24", "Demo Bitrix24 migration", "connected"),
    ):
        demo_account = ConnectorAccount(
            tenant_id=tenant.id,
            connector_code=code,
            title=title,
            status=status,
            credentials_json="e30=",
            credentials_encrypted=True,
            settings_json=json.dumps({}),
            sync_cursor=f"demo-{code}-cursor",
            last_sync_at=now() - timedelta(days=1) if status == "connected" else None,
        )
        db.add(demo_account)
        db.flush()
        db.add(
            ConnectorSyncRun(
                tenant_id=tenant.id,
                account_id=demo_account.id,
                direction="inbound",
                status="queued" if status == "placeholder" else "success",
                job_type=f"{code}_sync",
                attempt=1,
                max_attempts=3,
                created_count=0 if status == "placeholder" else 2,
                updated_count=0,
                failed_count=0,
                message=f"{title} ready",
                error_details_json="{}",
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


def create_communication_events(db: Session, tenant: Tenant, user: User) -> None:
    contacts = db.query(Contact).filter(Contact.tenant_id == tenant.id).order_by(Contact.created_at.asc()).all()
    for index, contact in enumerate(contacts[:5]):
        company = db.query(Company).filter(Company.id == contact.company_id).one()
        deal = (
            db.query(Deal)
            .filter(Deal.tenant_id == tenant.id, Deal.company_id == company.id)
            .order_by(Deal.created_at.desc())
            .first()
        )
        rows = [
            (
                "email",
                "inbound",
                f"Re: {deal.title if deal else 'CRM project'}",
                f"{contact.name} просит уточнить сроки внедрения, миграцию данных и следующий шаг по компании {company.name}.",
                contact.email,
                "sales@cmrsales.app",
                -index,
            ),
            (
                "call",
                "inbound",
                "Incoming sales call",
                f"Клиент {company.name} подтвердил интерес и попросил назначить встречу с техническим специалистом.",
                contact.phone,
                "+7 495 000-00-00",
                -index - 1,
            ),
            (
                "calendar",
                "inbound",
                "Discovery meeting scheduled",
                f"Встреча по требованиям {company.name}: интеграции, роли пользователей, RAG и отчетность.",
                contact.email,
                "calendar@cmrsales.app",
                index + 1,
            ),
        ]
        if index < 2:
            rows.append(
                (
                    "telegram" if index == 0 else "whatsapp",
                    "inbound",
                    "Messenger request",
                    f"{contact.name} написал в мессенджер и попросил короткую сводку по предложению.",
                    contact.phone,
                    "sales-manager",
                    -index,
                )
            )
        for channel, direction, subject, body, sender, recipient, shift in rows:
            db.add(
                CommunicationEvent(
                    tenant_id=tenant.id,
                    company_id=company.id,
                    contact_id=contact.id,
                    deal_id=deal.id if deal else None,
                    channel=channel,
                    direction=direction,
                    status="linked",
                    external_id=f"demo-{channel}-{contact.id}-{shift}",
                    sender=sender,
                    recipient=recipient,
                    occurred_at=now() + timedelta(days=shift),
                    subject=subject,
                    body=body,
                    ai_summary=f"{channel.upper()}: {subject}. {body}",
                    metadata_json=json.dumps({"demo": True, "source": "seed_demo"}, ensure_ascii=False),
                    created_by=user.id,
                    created_at=now() + timedelta(days=shift),
                    updated_at=now() + timedelta(days=shift),
                )
            )


def seed() -> None:
    db = SessionLocal()
    try:
        remove_existing_demo(db)

        tenant = Tenant(name="Demo AI Sales OS", slug=DEMO_TENANT_SLUG, is_active=True)
        user = User(
            email=DEMO_USER_EMAIL,
            full_name="Demo Sales Owner",
            avatar_url="/avatars/demo-sales-owner.png",
            password_hash=hash_password(DEMO_USER_PASSWORD),
            is_active=True,
        )
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
        create_communication_events(db, tenant, user)
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
