from __future__ import annotations

import sys
import json
from datetime import timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.accounts.models import Tenant, User
from app.modules.activity.models import Activity
from app.modules.communication.models import CommunicationEvent
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument, KnowledgeQuery
from app.modules.sales.models import (
    Company,
    CompanyFile,
    Contact,
    CustomerInsight,
    Deal,
    Lead,
    Note,
    NextAction,
    Pipeline,
    PipelineStage,
    Task,
)
from scripts.dev_access import DEV_TENANT_SLUG, DEV_USER_EMAIL, ensure_dev_access, repair_development_schema, run_migrations
from scripts.seed_demo import create_company_pack, create_knowledge, create_pipeline, now


def clear_workspace(db: Session, tenant: Tenant) -> None:
    db.execute(text("UPDATE companies SET next_action_id = NULL WHERE tenant_id = :tenant_id"), {"tenant_id": tenant.id})
    db.execute(text("UPDATE deals SET next_action_id = NULL WHERE tenant_id = :tenant_id"), {"tenant_id": tenant.id})
    db.flush()
    for model in (
        KnowledgeQuery,
        KnowledgeChunk,
        KnowledgeDocument,
        CommunicationEvent,
        CompanyFile,
        CustomerInsight,
        Activity,
        Note,
        Task,
        NextAction,
        Deal,
        Lead,
        Contact,
        PipelineStage,
        Pipeline,
        Company,
    ):
        db.query(model).filter(model.tenant_id == tenant.id).delete(synchronize_session=False)
    db.commit()


def seed_workspace(db: Session, tenant: Tenant, user: User) -> None:
    stages = create_pipeline(db, tenant)
    specs = (
        ("Альфа Ритейл", "https://alpha-retail.example", "Retail", "Федеральная розничная сеть. Тестирует CRM для B2B-продаж и партнерского канала.", "Мария Волкова", "m.volkova@alpha-retail.example", "+7 999 100-10-01", "CRM rollout на 120 менеджеров", 4_800_000, 3, "partner", "Отправить финальное КП", 1),
        ("СибТех Инжиниринг", "https://sibtech.example", "Industrial", "Инжиниринговая компания. Нужна миграция сделок, задач и истории коммуникаций.", "Игорь Соколов", "i.sokolov@sibtech.example", "+7 999 100-10-02", "Миграция CRM и внедрение RAG", 3_200_000, 2, "site", "Согласовать пилотный контур", 3),
        ("Nova Logistics", "https://nova-logistics.example", "Logistics", "Логистический оператор. Нужна единая timeline по клиентам и филиалам.", "Алена Каримова", "a.karimova@nova-logistics.example", "+7 999 100-10-03", "AI workspace для коммерческого блока", 2_650_000, 1, "conference", "Провести discovery call", -1),
        ("FinBridge", "https://finbridge.example", "Fintech", "Финтех-платформа. Интерес к безопасному AI агенту и журналу действий.", "Дмитрий Орлов", "d.orlov@finbridge.example", "+7 999 100-10-04", "AI Agent и compliance timeline", 5_100_000, 0, "referral", "Подготовить security brief", 2),
        ("MedCloud СНГ", "https://medcloud.example", "HealthTech", "SaaS для клиник. Смотрит CRM для партнерских продаж и базы знаний.", "Екатерина Лазарева", "e.lazareva@medcloud.example", "+7 999 100-10-05", "CRM для партнерской сети", 1_900_000, 4, "webinar", "Передать в onboarding", 5),
        ("UrbanDom", "https://urbandom.example", "Real Estate", "Девелопер. Нужен контроль сделок, встреч, КП и документов по крупным клиентам.", "Павел Морозов", "p.morozov@urbandom.example", "+7 999 100-10-06", "CRM для корпоративных продаж", 3_750_000, 2, "web", "Назначить встречу с директором", 4),
        ("GreenEnergy Hub", "https://greenenergy.example", "Energy", "Интегратор солнечных станций. Требуется учет тендеров, партнеров и сервисных контрактов.", "Ольга Титова", "o.titova@greenenergy.example", "+7 999 100-10-07", "CRM для тендерного отдела", 6_300_000, 3, "tender", "Отправить расчет TCO", 2),
        ("EduPro Academy", "https://edupro.example", "EdTech", "Онлайн-академия для корпоративного обучения. Нужна сегментация B2B клиентов и повторные продажи.", "Роман Беляев", "r.belyaev@edupro.example", "+7 999 100-10-08", "Партнерская CRM для B2B обучения", 1_450_000, 1, "ads", "Подготовить демо для HRD", 6),
        ("AgroTrade Север", "https://agrotrade.example", "Agro", "Дистрибьютор сельхозтехники. Нужна история коммуникаций по дилерам и крупным хозяйствам.", "Наталья Кузнецова", "n.kuznetsova@agrotrade.example", "+7 999 100-10-09", "CRM для дилерской сети", 2_980_000, 2, "dealer", "Согласовать список интеграций", -2),
        ("Quantum Parts", "https://qparts.example", "Manufacturing", "Производитель комплектующих. Интерес к прогнозу сделок, файлам КП и AI-сводкам по клиентам.", "Сергей Нестеров", "s.nesterov@qparts.example", "+7 999 100-10-10", "AI CRM для экспортных продаж", 7_200_000, 4, "email", "Передать договор юристам", 1),
    )
    for index, spec in enumerate(specs):
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
        enrich_company(db, tenant, user, stages, spec, index)
    create_knowledge(db, tenant, user)
    db.commit()


def enrich_company(
    db: Session,
    tenant: Tenant,
    user: User,
    stages: list[PipelineStage],
    spec: tuple,
    index: int,
) -> None:
    company = db.query(Company).filter(Company.tenant_id == tenant.id, Company.name == spec[0]).one()
    contact = db.query(Contact).filter(Contact.tenant_id == tenant.id, Contact.company_id == company.id).first()
    primary_deal = db.query(Deal).filter(Deal.tenant_id == tenant.id, Deal.company_id == company.id).first()

    task_templates = (
        ("Проверить бюджет и сроки", "Зафиксировать бюджет, дедлайн внедрения и лицо, принимающее решение.", index + 1),
        ("Обновить AI summary", "Добавить в сводку риски, следующий шаг и статус документов.", index + 2),
        ("Подготовить follow-up письмо", "Собрать итоги последнего контакта и отправить клиенту письмо.", index + 3),
    )
    if index % 2 == 0:
        task_templates += (("Запросить технические требования", "Уточнить интеграции, телефонию, импорт истории и ограничения безопасности.", index + 4),)

    for title, description, due_shift in task_templates:
        db.add(
            Task(
                tenant_id=tenant.id,
                company_id=company.id,
                assigned_to_id=user.id,
                deal_id=primary_deal.id if primary_deal else None,
                title=title,
                description=description,
                due_at=now() + timedelta(days=due_shift),
                done_at=None,
                created_at=now() - timedelta(days=max(1, index % 5)),
            )
        )

    if index % 3 != 0:
        lead = Lead(
            tenant_id=tenant.id,
            company_id=company.id,
            contact_id=contact.id if contact else None,
            title=f"Дополнительный запрос: интеграции и обучение для {company.name}",
            source="email" if index % 2 else "web",
            status="new" if index % 2 else "qualified",
            created_at=now() - timedelta(days=index + 2),
        )
        db.add(lead)
        db.flush()
        db.add(
            Deal(
                tenant_id=tenant.id,
                company_id=company.id,
                lead_id=lead.id,
                stage_id=stages[min(len(stages) - 1, (index + 1) % len(stages))].id,
                title=f"Дополнительный модуль для {company.name}",
                amount=650_000 + index * 180_000,
                status="open",
                probability=min(90, 30 + index * 5),
                expected_next_event="Ожидаем: подтверждения состава работ",
                next_step="Согласовать scope дополнительного модуля",
                owner_id=user.id,
                created_at=now() - timedelta(days=index + 1),
            )
        )

    note_text = (
        f"{company.name}: главный риск - скорость согласования. "
        f"AI должен учитывать отрасль {spec[2]}, источник {spec[10]} и следующий шаг: {spec[11]}."
    )
    db.add(
        Note(
            tenant_id=tenant.id,
            company_id=company.id,
            author_id=user.id,
            deal_id=primary_deal.id if primary_deal else None,
            text=note_text,
            created_at=now() - timedelta(hours=index + 3),
        )
    )

    extra_activities = (
        ("EMAIL", "Email", "Клиент запросил детали по внедрению", "Отправлены материалы по срокам, интеграциям и безопасности."),
        ("COMMENT", "Message", "Внутренний комментарий менеджера", note_text),
        ("TASK", "CRM", "План действий обновлен", "Созданы задачи для follow-up, бюджета и технических требований."),
    )
    for shift, (activity_type, channel, title, description) in enumerate(extra_activities, start=1):
        db.add(
            Activity(
                tenant_id=tenant.id,
                company_id=company.id,
                contact_id=contact.id if contact else None,
                deal_id=primary_deal.id if primary_deal else None,
                type=activity_type,
                channel=channel,
                title=title,
                description=description,
                created_by=user.id,
                metadata_json=json.dumps({"demo": True, "interpretable": True, "company": company.name}, ensure_ascii=False),
                created_at=now() - timedelta(days=shift, minutes=index * 7),
            )
        )


def main() -> None:
    run_migrations()
    repair_development_schema()
    db = SessionLocal()
    try:
        ensure_dev_access(db)
        tenant = db.query(Tenant).filter(Tenant.slug == DEV_TENANT_SLUG).one()
        user = db.query(User).filter(User.email == DEV_USER_EMAIL).one()
        clear_workspace(db, tenant)
        seed_workspace(db, tenant, user)
    finally:
        db.close()

    print("Developer workspace seeded")
    print("Companies: 10")
    print(f"Login: {DEV_USER_EMAIL}")
    print("Password: configured via DEV_USER_PASSWORD")


if __name__ == "__main__":
    main()
