import json
import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.activity.service import ActivityService
from app.modules.ai_agent.models import AgentAction, AgentMessage
from app.modules.knowledge.service import KnowledgeService
from app.modules.sales.models import Deal, Lead, Note, PipelineStage, Task


class AgentService:
    def __init__(self, db: Session):
        self.db = db
        self.knowledge_service = KnowledgeService(db)

    def chat(self, tenant_id: UUID, user_id: UUID, message: str) -> tuple[str, list[AgentAction], list[dict]]:
        self._save_message(tenant_id, user_id, "user", message)

        lowered = message.lower()
        actions: list[AgentAction] = []
        sources: list[dict] = []

        if self._looks_like_task_request(lowered):
            action = self._propose_task(tenant_id, user_id, message)
            if action is None:
                answer = "Для создания задачи нужна компания или сделка. Укажи название сделки или оставь в workspace одну компанию."
            else:
                actions.append(action)
                answer = "Могу создать задачу. Проверь предложение и подтверди действие."
        elif self._looks_like_deal_move_request(lowered):
            action = self._propose_deal_move(tenant_id, user_id, message)
            if action is None:
                answer = "Не нашла подходящую сделку или этап. Укажи название сделки и этап точнее."
            else:
                actions.append(action)
                answer = "Могу перенести сделку. Проверь предложение и подтверди действие."
        elif self._looks_like_summary_request(lowered):
            answer = self._summarize_crm(tenant_id)
        else:
            answer, sources = self._answer_from_knowledge(tenant_id, user_id, message)

        self._save_message(tenant_id, user_id, "assistant", answer)
        return answer, actions, sources

    def list_history(self, tenant_id: UUID, limit: int = 30) -> list[AgentMessage]:
        return (
            self.db.query(AgentMessage)
            .filter(AgentMessage.tenant_id == tenant_id)
            .order_by(AgentMessage.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_actions(self, tenant_id: UUID) -> list[AgentAction]:
        return (
            self.db.query(AgentAction)
            .filter(AgentAction.tenant_id == tenant_id)
            .order_by(AgentAction.created_at.desc())
            .limit(30)
            .all()
        )

    def confirm_action(self, tenant_id: UUID, action_id: UUID) -> AgentAction | None:
        action = (
            self.db.query(AgentAction)
            .filter(AgentAction.id == action_id, AgentAction.tenant_id == tenant_id)
            .one_or_none()
        )
        if action is None:
            return None
        if action.status != "pending":
            return action

        payload = json.loads(action.payload_json)
        if action.action_type == "create_task":
            task = Task(
                tenant_id=tenant_id,
                company_id=UUID(payload["company_id"]),
                assigned_to_id=action.user_id,
                title=payload["title"],
                description=payload.get("description"),
                deal_id=payload.get("deal_id"),
            )
            self.db.add(task)
            self.db.flush()
            ActivityService(self.db).create(
                tenant_id=tenant_id,
                created_by=action.user_id,
                company_id=task.company_id,
                deal_id=task.deal_id,
                activity_type="AI_ACTION",
                title="AI created task",
                description=task.title,
                metadata={"action_id": str(action.id), "task_id": str(task.id)},
                commit=False,
            )
            action.result_json = json.dumps({"task_id": str(task.id), "title": task.title})
        elif action.action_type == "move_deal":
            deal = (
                self.db.query(Deal)
                .filter(Deal.id == UUID(payload["deal_id"]), Deal.tenant_id == tenant_id)
                .one_or_none()
            )
            if deal is None:
                action.status = "failed"
                action.result_json = json.dumps({"error": "Deal not found"})
                self.db.commit()
                return action
            deal.stage_id = UUID(payload["stage_id"])
            ActivityService(self.db).create(
                tenant_id=tenant_id,
                created_by=action.user_id,
                company_id=deal.company_id,
                deal_id=deal.id,
                activity_type="AI_ACTION",
                title="AI moved deal",
                description=f"{deal.title} moved to {payload.get('stage_name', 'new stage')}",
                metadata={"action_id": str(action.id), "stage_id": payload["stage_id"]},
                commit=False,
            )
            action.result_json = json.dumps({"deal_id": str(deal.id), "stage_id": str(deal.stage_id)})
        else:
            action.status = "failed"
            action.result_json = json.dumps({"error": "Unknown action"})
            self.db.commit()
            return action

        action.status = "confirmed"
        action.confirmed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(action)
        return action

    def reject_action(self, tenant_id: UUID, action_id: UUID) -> AgentAction | None:
        action = (
            self.db.query(AgentAction)
            .filter(AgentAction.id == action_id, AgentAction.tenant_id == tenant_id)
            .one_or_none()
        )
        if action is None:
            return None
        if action.status == "pending":
            action.status = "rejected"
            self.db.commit()
            self.db.refresh(action)
        return action

    def _answer_from_knowledge(self, tenant_id: UUID, user_id: UUID, message: str) -> tuple[str, list[dict]]:
        answer, ranked_chunks = self.knowledge_service.answer(tenant_id, user_id, message, limit=5)
        sources = [
            {
                "document_id": str(item.document.id),
                "document_title": item.document.title,
                "chunk_id": str(item.chunk.id),
                "score": item.score,
                "text": item.chunk.text[:500],
            }
            for item in ranked_chunks
        ]
        return answer, sources

    def _summarize_crm(self, tenant_id: UUID) -> str:
        leads_count = self.db.query(Lead).filter(Lead.tenant_id == tenant_id).count()
        deals = self.db.query(Deal).filter(Deal.tenant_id == tenant_id).all()
        open_tasks = (
            self.db.query(Task)
            .filter(Task.tenant_id == tenant_id, Task.done_at.is_(None))
            .count()
        )
        amount = sum(float(deal.amount or 0) for deal in deals)
        return (
            f"Сводка: лидов {leads_count}, сделок {len(deals)}, "
            f"открытых задач {open_tasks}, сумма пайплайна {amount:,.0f} руб."
        )

    def _propose_task(self, tenant_id: UUID, user_id: UUID, message: str) -> AgentAction | None:
        deal = self._find_deal_from_text(tenant_id, message)
        company_id = deal.company_id if deal else self._find_single_company_id(tenant_id)
        if company_id is None:
            return None
        title = self._extract_task_title(message)
        action = AgentAction(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="create_task",
            payload_json=json.dumps(
                {
                    "company_id": str(company_id),
                    "title": title,
                    "description": f"Создано AI агентом из запроса: {message}",
                    "deal_id": str(deal.id) if deal else None,
                }
            ),
        )
        self.db.add(action)
        self.db.commit()
        self.db.refresh(action)
        return action

    def _propose_deal_move(self, tenant_id: UUID, user_id: UUID, message: str) -> AgentAction | None:
        deal = self._find_deal_from_text(tenant_id, message)
        stage = self._find_stage_from_text(tenant_id, message)
        if deal is None or stage is None:
            return None

        action = AgentAction(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type="move_deal",
            payload_json=json.dumps(
                {
                    "deal_id": str(deal.id),
                    "deal_title": deal.title,
                    "stage_id": str(stage.id),
                    "stage_name": stage.name,
                }
            ),
        )
        self.db.add(action)
        self.db.commit()
        self.db.refresh(action)
        return action

    def _find_deal_from_text(self, tenant_id: UUID, text: str) -> Deal | None:
        deals = self.db.query(Deal).filter(Deal.tenant_id == tenant_id).all()
        lowered = text.lower()
        for deal in deals:
            if deal.title.lower() in lowered:
                return deal
        return deals[0] if len(deals) == 1 else None

    def _find_stage_from_text(self, tenant_id: UUID, text: str) -> PipelineStage | None:
        stages = self.db.query(PipelineStage).filter(PipelineStage.tenant_id == tenant_id).all()
        lowered = text.lower()
        for stage in stages:
            if stage.name.lower() in lowered:
                return stage
        return None

    def _find_single_company_id(self, tenant_id: UUID) -> UUID | None:
        from app.modules.sales.models import Company

        companies = self.db.query(Company).filter(Company.tenant_id == tenant_id).all()
        return companies[0].id if len(companies) == 1 else None

    def _extract_task_title(self, message: str) -> str:
        cleaned = re.sub(r"\b(создай|создать|задачу|задача|нужно)\b", "", message, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
        return cleaned[:255] if cleaned else "Связаться с клиентом"

    def _save_message(self, tenant_id: UUID, user_id: UUID, role: str, content: str) -> None:
        self.db.add(AgentMessage(tenant_id=tenant_id, user_id=user_id, role=role, content=content))
        self.db.commit()

    def _looks_like_task_request(self, lowered: str) -> bool:
        return "задач" in lowered or "напомни" in lowered or "создай task" in lowered

    def _looks_like_deal_move_request(self, lowered: str) -> bool:
        return ("перенеси" in lowered or "перемести" in lowered) and "сдел" in lowered

    def _looks_like_summary_request(self, lowered: str) -> bool:
        return "сводк" in lowered or "итог" in lowered or "что по crm" in lowered or "обзор" in lowered
