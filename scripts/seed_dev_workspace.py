from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.accounts.models import Tenant, User
from app.modules.activity.models import Activity
from app.modules.sales.models import (
    Company,
    CompanyFile,
    Contact,
    CustomerInsight,
    Deal,
    Lead,
    Note,
    Pipeline,
    PipelineStage,
    Task,
)
from scripts.dev_access import DEV_TENANT_SLUG, DEV_USER_EMAIL, ensure_dev_access, repair_development_schema, run_migrations
from scripts.seed_demo import create_company_pack, create_knowledge, create_pipeline


def clear_workspace(db: Session, tenant: Tenant) -> None:
    for model in (
        CompanyFile,
        CustomerInsight,
        Activity,
        Note,
        Task,
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
    )
    for spec in specs:
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
    db.commit()


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
    print("Companies: 6")
    print(f"Login: {DEV_USER_EMAIL}")
    print("Password: password123")


if __name__ == "__main__":
    main()
