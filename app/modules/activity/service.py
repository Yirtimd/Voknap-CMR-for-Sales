import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.activity.models import Activity


class ActivityService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        tenant_id: UUID,
        activity_type: str,
        title: str,
        created_by: UUID | None = None,
        description: str | None = None,
        company_id: UUID | None = None,
        contact_id: UUID | None = None,
        deal_id: UUID | None = None,
        channel: str | None = None,
        metadata: dict | None = None,
        commit: bool = True,
    ) -> Activity:
        activity = Activity(
            tenant_id=tenant_id,
            company_id=company_id,
            contact_id=contact_id,
            deal_id=deal_id,
            type=activity_type,
            channel=channel,
            title=title,
            description=description,
            created_by=created_by,
            metadata_json=json.dumps(metadata or {}),
        )
        self.db.add(activity)
        if commit:
            self.db.commit()
            self.db.refresh(activity)
        return activity

    def list(
        self,
        tenant_id: UUID,
        company_id: UUID | None = None,
        contact_id: UUID | None = None,
        deal_id: UUID | None = None,
        activity_type: str | None = None,
        limit: int = 100,
    ) -> list[Activity]:
        query = self.db.query(Activity).filter(Activity.tenant_id == tenant_id)
        if company_id:
            query = query.filter(Activity.company_id == company_id)
        if contact_id:
            query = query.filter(Activity.contact_id == contact_id)
        if deal_id:
            query = query.filter(Activity.deal_id == deal_id)
        if activity_type:
            query = query.filter(Activity.type == activity_type)
        return query.order_by(Activity.created_at.desc()).limit(limit).all()
