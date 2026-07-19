import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.accounts.models import (
    AssignmentRule,
    LeadQueue,
    LeadQueueMember,
    Membership,
    SalesTeam,
    Territory,
)
from app.modules.sales.models import Company, Lead


ALLOWED_CRITERIA = {
    "company": {"industry", "country_code", "region", "company_type", "status"},
    "lead": {"source", "status", "company_industry", "company_country_code", "company_region"},
}


@dataclass(frozen=True)
class Assignment:
    owner_id: UUID | None = None
    queue_id: UUID | None = None
    territory_id: UUID | None = None


def validate_criteria(entity_type: str, criteria: dict[str, str]) -> None:
    invalid = set(criteria) - ALLOWED_CRITERIA[entity_type]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported criteria: {', '.join(sorted(invalid))}",
        )


def validate_target(db: Session, tenant_id: UUID, target_type: str, target_id: UUID) -> None:
    model = {
        "member": Membership,
        "team": SalesTeam,
        "queue": LeadQueue,
        "territory": Territory,
    }[target_type]
    query = db.query(model).filter(model.tenant_id == tenant_id, model.id == target_id)
    target = query.one_or_none()
    if target is None or not target.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active target not found")


def assign_company(db: Session, tenant_id: UUID, values: dict[str, Any]) -> Assignment:
    rule = _matching_rule(db, tenant_id, "company", values)
    if rule is not None:
        return _resolve_target(db, tenant_id, rule, "company")

    territory = _matching_territory(db, tenant_id, values)
    if territory is None:
        return Assignment()
    owner_id = _territory_owner(db, territory)
    return Assignment(owner_id=owner_id, territory_id=territory.id)


def assign_lead(
    db: Session,
    tenant_id: UUID,
    values: dict[str, Any],
    company: Company,
) -> Assignment:
    enriched = {
        **values,
        "company_industry": company.industry,
        "company_country_code": company.country_code,
        "company_region": company.region,
    }
    rule = _matching_rule(db, tenant_id, "lead", enriched)
    if rule is None:
        return Assignment(owner_id=company.owner_id, territory_id=company.territory_id)
    return _resolve_target(db, tenant_id, rule, "lead")


def next_queue_owner(db: Session, tenant_id: UUID, queue: LeadQueue) -> UUID | None:
    members = (
        db.query(Membership)
        .join(
            LeadQueueMember,
            (LeadQueueMember.tenant_id == Membership.tenant_id)
            & (LeadQueueMember.membership_id == Membership.id),
        )
        .filter(
            LeadQueueMember.tenant_id == tenant_id,
            LeadQueueMember.queue_id == queue.id,
            LeadQueueMember.is_active.is_(True),
            Membership.is_active.is_(True),
        )
        .order_by(Membership.created_at, Membership.id)
        .all()
    )
    if not members:
        return None
    member = members[queue.routing_cursor % len(members)]
    queue.routing_cursor = (queue.routing_cursor + 1) % len(members)
    return member.user_id


def _matching_rule(
    db: Session,
    tenant_id: UUID,
    entity_type: str,
    values: dict[str, Any],
) -> AssignmentRule | None:
    rules = (
        db.query(AssignmentRule)
        .filter(
            AssignmentRule.tenant_id == tenant_id,
            AssignmentRule.entity_type == entity_type,
            AssignmentRule.is_active.is_(True),
        )
        .order_by(AssignmentRule.priority, AssignmentRule.created_at)
        .all()
    )
    for rule in rules:
        criteria = json.loads(rule.criteria_json)
        if all(_same(values.get(field), expected) for field, expected in criteria.items()):
            return rule
    return None


def _matching_territory(
    db: Session,
    tenant_id: UUID,
    values: dict[str, Any],
) -> Territory | None:
    territories = (
        db.query(Territory)
        .filter(Territory.tenant_id == tenant_id, Territory.is_active.is_(True))
        .order_by(Territory.priority, Territory.created_at)
        .all()
    )
    for territory in territories:
        filters = {
            "country_code": territory.country_code,
            "region": territory.region,
            "industry": territory.industry,
        }
        if all(expected is None or _same(values.get(field), expected) for field, expected in filters.items()):
            return territory
    return None


def _resolve_target(
    db: Session,
    tenant_id: UUID,
    rule: AssignmentRule,
    entity_type: str,
) -> Assignment:
    if rule.target_type == "member":
        return Assignment(owner_id=rule.assignee_id)
    if rule.target_type == "team":
        return Assignment(owner_id=_least_loaded_team_member(db, tenant_id, rule.team_id, entity_type))
    if rule.target_type == "queue":
        queue = db.get(LeadQueue, rule.queue_id)
        if queue is None or not queue.is_active:
            return Assignment()
        owner_id = next_queue_owner(db, tenant_id, queue) if queue.strategy == "round_robin" else None
        return Assignment(owner_id=owner_id, queue_id=queue.id)

    territory = db.get(Territory, rule.territory_id)
    if territory is None or not territory.is_active:
        return Assignment()
    return Assignment(owner_id=_territory_owner(db, territory), territory_id=territory.id)


def _territory_owner(db: Session, territory: Territory) -> UUID | None:
    if territory.owner_membership_id is not None:
        member = db.get(Membership, territory.owner_membership_id)
        return member.user_id if member is not None and member.is_active else None
    if territory.team_id is not None:
        return _least_loaded_team_member(db, territory.tenant_id, territory.team_id, "company")
    return None


def _least_loaded_team_member(
    db: Session,
    tenant_id: UUID,
    team_id: UUID | None,
    entity_type: str,
) -> UUID | None:
    if team_id is None:
        return None
    model = Lead if entity_type == "lead" else Company
    candidates = (
        db.query(Membership.user_id, func.count(model.id).label("workload"))
        .outerjoin(
            model,
            (model.tenant_id == Membership.tenant_id) & (model.owner_id == Membership.user_id),
        )
        .filter(
            Membership.tenant_id == tenant_id,
            Membership.team_id == team_id,
            Membership.is_active.is_(True),
        )
        .group_by(Membership.user_id, Membership.created_at)
        .order_by("workload", Membership.created_at)
        .all()
    )
    return candidates[0].user_id if candidates else None


def _same(actual: Any, expected: Any) -> bool:
    if actual is None:
        return False
    return str(actual).strip().casefold() == str(expected).strip().casefold()
