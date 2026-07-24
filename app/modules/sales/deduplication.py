import json
import re
from collections import defaultdict
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.sales.models import Contact, Deal, DuplicateCandidate, Lead


ENTITY_MODELS = {"contacts": Contact, "leads": Lead, "deals": Deal}


def scan_duplicates(
    db: Session,
    tenant_id: UUID,
    entity_type: str,
    actor_id: UUID,
    minimum_score: int,
    limit: int,
) -> int:
    model = ENTITY_MODELS[entity_type]
    rows = (
        db.query(model)
        .filter(
            model.tenant_id == tenant_id,
            model.deleted_at.is_(None),
            model.is_archived.is_(False),
        )
        .order_by(model.created_at.desc())
        .limit(2000)
        .all()
    )
    buckets: dict[str, list] = defaultdict(list)
    for row in rows:
        for key in _blocking_keys(entity_type, row):
            buckets[key].append(row)

    pairs: dict[tuple[UUID, UUID], tuple[int, list[str]]] = {}
    for bucket in buckets.values():
        for index, first in enumerate(bucket):
            for second in bucket[index + 1 :]:
                a_id, b_id = sorted((first.id, second.id), key=str)
                score, matched = _score(entity_type, first, second)
                if score >= minimum_score:
                    previous = pairs.get((a_id, b_id))
                    if previous is None or score > previous[0]:
                        pairs[(a_id, b_id)] = (score, matched)
                if len(pairs) >= limit:
                    break

    count = 0
    for (record_a_id, record_b_id), (score, matched) in pairs.items():
        candidate = (
            db.query(DuplicateCandidate)
            .filter(
                DuplicateCandidate.tenant_id == tenant_id,
                DuplicateCandidate.entity_type == entity_type,
                DuplicateCandidate.record_a_id == record_a_id,
                DuplicateCandidate.record_b_id == record_b_id,
            )
            .one_or_none()
        )
        if candidate is None:
            candidate = DuplicateCandidate(
                tenant_id=tenant_id,
                entity_type=entity_type,
                record_a_id=record_a_id,
                record_b_id=record_b_id,
                detected_by_id=actor_id,
            )
            db.add(candidate)
        if candidate.status != "merged":
            candidate.score = score
            candidate.matched_fields_json = json.dumps(matched)
            if candidate.status != "dismissed":
                candidate.status = "open"
        count += 1
    db.commit()
    return count


def _blocking_keys(entity_type: str, row) -> set[str]:
    if entity_type == "contacts":
        return {
            key
            for key in (
                f"email:{_text(row.email)}" if row.email else "",
                f"phone:{_phone(row.phone)}" if row.phone else "",
                f"name:{row.company_id}:{_text(row.name)}",
            )
            if key and not key.endswith(":")
        }
    if entity_type == "leads":
        return {
            key
            for key in {
            f"title:{row.company_id}:{_text(row.title)}",
            f"contact:{row.contact_id}" if row.contact_id else "",
            }
            if key
        }
    return {f"title:{row.company_id}:{_text(row.title)}"}


def _score(entity_type: str, first, second) -> tuple[int, list[str]]:
    matched: list[str] = []
    score = 0
    if entity_type == "contacts":
        if first.email and _text(first.email) == _text(second.email):
            score, matched = 100, ["email"]
        if first.phone and _phone(first.phone) == _phone(second.phone):
            score, matched = max(score, 98), [*matched, "phone"]
        if first.company_id == second.company_id and _text(first.name) == _text(second.name):
            score, matched = max(score, 90), [*matched, "name", "company_id"]
    else:
        if first.company_id == second.company_id and _text(first.title) == _text(second.title):
            score, matched = 90, ["title", "company_id"]
        if entity_type == "leads" and first.contact_id and first.contact_id == second.contact_id:
            score, matched = max(score, 95), [*matched, "contact_id"]
    return score, sorted(set(matched))


def _text(value: str | None) -> str:
    return re.sub(r"[^a-zа-я0-9]+", "", (value or "").casefold())


def _phone(value: str | None) -> str:
    return re.sub(r"\D+", "", value or "")[-10:]
