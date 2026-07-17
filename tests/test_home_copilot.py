from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.main  # noqa: F401 - registers every model in shared metadata
from app.core.database import Base
from app.modules.ai_agent.service import AgentService
from app.modules.sales.models import Company, Deal, NextAction, Pipeline, PipelineStage


def test_home_copilot_uses_backend_risk_ranking_and_next_action():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    tenant_id = uuid4()

    with Session(engine) as db:
        safe_company = Company(tenant_id=tenant_id, name="Large Safe Account")
        risky_company = Company(tenant_id=tenant_id, name="Risk Account")
        pipeline = Pipeline(tenant_id=tenant_id, name="Sales")
        db.add_all([safe_company, risky_company, pipeline])
        db.flush()
        stage = PipelineStage(
            tenant_id=tenant_id,
            pipeline_id=pipeline.id,
            name="Negotiation",
        )
        db.add(stage)
        db.flush()
        safe_deal = Deal(
            tenant_id=tenant_id,
            company_id=safe_company.id,
            stage_id=stage.id,
            title="Large safe deal",
            amount=10_000_000,
            probability=90,
            risk_level="low",
            next_step="Wait for signature",
        )
        risky_deal = Deal(
            tenant_id=tenant_id,
            company_id=risky_company.id,
            stage_id=stage.id,
            title="Smaller risky deal",
            amount=1_000_000,
            probability=20,
            risk_level="high",
            expected_close_date=datetime.now(timezone.utc) - timedelta(days=3),
        )
        db.add_all([safe_deal, risky_deal])
        db.flush()
        next_action = NextAction(
            tenant_id=tenant_id,
            company_id=risky_company.id,
            deal_id=risky_deal.id,
            title="Позвонить клиенту и согласовать новый срок",
            priority="urgent",
            status="open",
        )
        db.add(next_action)
        db.commit()

        result = AgentService(db).home_copilot(tenant_id)

    assert result["source"] == "backend_copilot"
    assert result["deal_id"] == risky_deal.id
    assert result["company_id"] == risky_company.id
    assert result["title"] == next_action.title
    assert result["action_label"] == "Позвонить"
    assert result["risk_score"] > 70
    assert result["focus_deals"][0]["deal_id"] == risky_deal.id
    assert result["focus_deals"][0]["stage_name"] == "Переговоры"
    assert "этап «Переговоры»" in result["rationale"]
