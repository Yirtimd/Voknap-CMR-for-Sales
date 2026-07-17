import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentTenant, get_current_tenant
from app.modules.activity.service import ActivityService
from app.modules.accounts.models import User
from app.modules.knowledge.models import KnowledgeDocument
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
from app.modules.sales.stages import stage_label_ru
from app.modules.sales.schemas import (
    CompanyCreate,
    CompanyFileCreate,
    CompanyFileResponse,
    CompanyResponse,
    CompanyUpdate,
    CompanyWorkspaceResponse,
    ContactCreate,
    ContactResponse,
    CustomerInsightResponse,
    CustomerInsightUpsert,
    DealCreate,
    DealMoveRequest,
    DealResponse,
    LeadCreate,
    LeadResponse,
    NextActionCreate,
    NextActionDoneRequest,
    NextActionResponse,
    NoteCreate,
    NoteResponse,
    PipelineCreate,
    PipelineResponse,
    TaskCreate,
    TaskDoneRequest,
    TaskResponse,
    OwnerResponse,
)


router = APIRouter()


@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> Company:
    company = Company(tenant_id=tenant.id, **payload.model_dump())
    db.add(company)
    db.flush()
    ActivityService(db).create(
        tenant_id=tenant.id,
        created_by=tenant.user_id,
        company_id=company.id,
        activity_type="SYSTEM",
        title="Company created",
        description=company.name,
        metadata={"company_id": str(company.id)},
        commit=False,
    )
    db.commit()
    db.refresh(company)
    return company


@router.get("/companies", response_model=list[CompanyResponse])
def list_companies(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[Company]:
    return db.query(Company).filter(Company.tenant_id == tenant.id).order_by(Company.created_at.desc()).all()


@router.patch("/companies/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: UUID,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> CompanyResponse:
    company = _get_for_tenant(db, Company, tenant.id, company_id)
    changes = []
    update_data = payload.model_dump(exclude_unset=True)
    for field_name, new_value in update_data.items():
        old_value = getattr(company, field_name)
        if old_value == new_value:
            continue
        setattr(company, field_name, new_value)
        changes.append({
            "field": field_name,
            "old": _metadata_value(old_value),
            "new": _metadata_value(new_value),
        })

    if changes:
        ActivityService(db).create(
            tenant_id=tenant.id,
            created_by=tenant.user_id,
            company_id=company.id,
            activity_type="SYSTEM",
            channel="CRM",
            title="Company fields changed",
            description=", ".join(change["field"] for change in changes),
            metadata={"changes": changes},
            commit=False,
        )

    db.commit()
    db.refresh(company)
    owner = db.query(User).filter(User.id == company.owner_id).one_or_none() if company.owner_id else None
    return _company_response(company, owner, _company_source(company, db, tenant.id))


@router.get("/companies/{company_id}", response_model=CompanyWorkspaceResponse)
def company_workspace(
    company_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> CompanyWorkspaceResponse:
    company = _get_for_tenant(db, Company, tenant.id, company_id)
    contacts = (
        db.query(Contact)
        .filter(Contact.tenant_id == tenant.id, Contact.company_id == company.id)
        .order_by(Contact.created_at.desc())
        .all()
    )
    deals = db.query(Deal).filter(Deal.tenant_id == tenant.id, Deal.company_id == company.id).all()
    tasks = db.query(Task).filter(Task.tenant_id == tenant.id, Task.company_id == company.id).all()
    files = (
        db.query(CompanyFile)
        .filter(CompanyFile.tenant_id == tenant.id, CompanyFile.company_id == company.id)
        .order_by(CompanyFile.created_at.desc())
        .all()
    )
    knowledge_documents = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.tenant_id == tenant.id, KnowledgeDocument.company_id == company.id)
        .order_by(KnowledgeDocument.created_at.desc())
        .all()
    )
    insight = (
        db.query(CustomerInsight)
        .filter(CustomerInsight.tenant_id == tenant.id, CustomerInsight.company_id == company.id)
        .one_or_none()
    )
    next_action = _resolve_company_next_action(db, tenant.id, company)
    owner = db.query(User).filter(User.id == company.owner_id).one_or_none() if company.owner_id else None
    related_activities = ActivityService(db).list(tenant_id=tenant.id, company_id=company.id, limit=80)
    author_ids = [activity.created_by for activity in related_activities if activity.created_by]
    authors = {
        user.id: user
        for user in db.query(User).filter(User.id.in_(author_ids)).all()
    } if author_ids else {}
    open_tasks = [task for task in tasks if task.done_at is None]
    total_amount = sum(float(deal.amount or 0) for deal in deals)
    activity_rows = [
        _activity_workspace_response(activity, authors.get(activity.created_by))
        for activity in related_activities
    ]
    contact_activities = [
        row for row in activity_rows
        if row["activity_type"] in {"call", "email", "meeting", "message"}
    ]
    last_contact = contact_activities[0] if contact_activities else None
    channel_summary = _channel_summary(activity_rows)
    company_source = _company_source(company, db, tenant.id)
    ai_summary = (
        f"{company.name}: контактов {len(contacts)}, сделок {len(deals)}, "
        f"открытых задач {len(open_tasks)}, пайплайн {total_amount:,.0f} руб."
    )
    ai_insights = []
    if not contacts:
        ai_insights.append("Добавить ключевых контактов компании.")
    if deals and not open_tasks:
        ai_insights.append("Создать follow-up задачу по активным сделкам.")
    if not deals:
        ai_insights.append("Создать первую сделку или связать лид с компанией.")

    return CompanyWorkspaceResponse(
        company=_company_response(company, owner, company_source),
        overview={
            "contacts_count": len(contacts),
            "deals_count": len(deals),
            "open_tasks_count": len(open_tasks),
            "pipeline_amount": total_amount,
            "last_contact_at": last_contact["created_at"] if last_contact else None,
            "last_contact_person": last_contact["author_name"] if last_contact else None,
            "channel_summary": channel_summary,
        },
        health=_health_response(insight, contacts, deals),
        next_action=_next_action_dict(next_action) if next_action else None,
        contacts=[_contact_response(contact) for contact in contacts],
        deals=[_deal_response(deal) for deal in deals],
        tasks=tasks,
        activities=activity_rows,
        files=[_file_response(file) for file in files],
        knowledge_documents=[_knowledge_document_response(document) for document in knowledge_documents],
        ai_summary=ai_summary,
        ai_insights=ai_insights,
    )


@router.get("/companies/{company_id}/files", response_model=list[CompanyFileResponse])
def list_company_files(
    company_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[CompanyFileResponse]:
    _get_for_tenant(db, Company, tenant.id, company_id)
    files = (
        db.query(CompanyFile)
        .filter(CompanyFile.tenant_id == tenant.id, CompanyFile.company_id == company_id)
        .order_by(CompanyFile.created_at.desc())
        .all()
    )
    return [_company_file_response(file) for file in files]


@router.post("/companies/{company_id}/files", response_model=CompanyFileResponse, status_code=status.HTTP_201_CREATED)
def create_company_file(
    company_id: UUID,
    payload: CompanyFileCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> CompanyFileResponse:
    _get_for_tenant(db, Company, tenant.id, company_id)
    if payload.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="company_id does not match path")
    if payload.deal_id is not None:
        deal = _get_for_tenant(db, Deal, tenant.id, payload.deal_id)
        if deal.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deal belongs to another company")
    if payload.contact_id is not None:
        contact = _get_for_tenant(db, Contact, tenant.id, payload.contact_id)
        if contact.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contact belongs to another company")

    file = CompanyFile(
        tenant_id=tenant.id,
        uploaded_by_id=tenant.user_id,
        **payload.model_dump(),
    )
    db.add(file)
    db.flush()
    ActivityService(db).create(
        tenant_id=tenant.id,
        created_by=tenant.user_id,
        company_id=company_id,
        deal_id=payload.deal_id,
        contact_id=payload.contact_id,
        activity_type="FILE_UPLOADED",
        channel="File",
        title="File uploaded",
        description=payload.name,
        metadata={"file_id": str(file.id), "file_type": payload.file_type},
        commit=False,
    )
    db.commit()
    db.refresh(file)
    return _company_file_response(file)


@router.get("/companies/{company_id}/insight", response_model=CustomerInsightResponse)
def get_customer_insight(
    company_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> CustomerInsightResponse:
    _get_for_tenant(db, Company, tenant.id, company_id)
    insight = (
        db.query(CustomerInsight)
        .filter(CustomerInsight.tenant_id == tenant.id, CustomerInsight.company_id == company_id)
        .one_or_none()
    )
    if insight is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CustomerInsight not found")
    return _customer_insight_response(insight)


@router.put("/companies/{company_id}/insight", response_model=CustomerInsightResponse)
def upsert_customer_insight(
    company_id: UUID,
    payload: CustomerInsightUpsert,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> CustomerInsightResponse:
    _get_for_tenant(db, Company, tenant.id, company_id)
    insight = (
        db.query(CustomerInsight)
        .filter(CustomerInsight.tenant_id == tenant.id, CustomerInsight.company_id == company_id)
        .one_or_none()
    )
    if insight is None:
        insight = CustomerInsight(tenant_id=tenant.id, company_id=company_id)
        db.add(insight)

    insight.health_score = payload.health_score
    insight.health_label = payload.health_label
    insight.health_trend = payload.health_trend
    insight.risk_level = payload.risk_level
    insight.success_chance = payload.success_chance
    insight.success_chance_delta = payload.success_chance_delta
    insight.ai_recommendations_json = json.dumps(payload.ai_recommendations, ensure_ascii=False)
    insight.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(insight)
    return _customer_insight_response(insight)


@router.post("/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> Contact:
    _get_for_tenant(db, Company, tenant.id, payload.company_id)
    contact = Contact(tenant_id=tenant.id, **payload.model_dump())
    db.add(contact)
    db.flush()
    ActivityService(db).create(
        tenant_id=tenant.id,
        created_by=tenant.user_id,
        company_id=contact.company_id,
        contact_id=contact.id,
        activity_type="SYSTEM",
        title="Contact created",
        description=contact.name,
        metadata={"contact_id": str(contact.id)},
        commit=False,
    )
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/contacts", response_model=list[ContactResponse])
def list_contacts(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[Contact]:
    return db.query(Contact).filter(Contact.tenant_id == tenant.id).order_by(Contact.created_at.desc()).all()


@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> Lead:
    _get_for_tenant(db, Company, tenant.id, payload.company_id)
    if payload.contact_id is not None:
        contact = _get_for_tenant(db, Contact, tenant.id, payload.contact_id)
        if contact.company_id != payload.company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contact belongs to another company")

    lead = Lead(tenant_id=tenant.id, **payload.model_dump())
    db.add(lead)
    db.flush()
    ActivityService(db).create(
        tenant_id=tenant.id,
        created_by=tenant.user_id,
        company_id=lead.company_id,
        contact_id=lead.contact_id,
        activity_type="SYSTEM",
        title="Lead created",
        description=lead.title,
        metadata={"lead_id": str(lead.id), "source": lead.source},
        commit=False,
    )
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/leads", response_model=list[LeadResponse])
def list_leads(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[Lead]:
    return db.query(Lead).filter(Lead.tenant_id == tenant.id).order_by(Lead.created_at.desc()).all()


@router.get("/leads/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> Lead:
    return _get_for_tenant(db, Lead, tenant.id, lead_id)


@router.post("/pipelines", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
def create_pipeline(
    payload: PipelineCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> Pipeline:
    pipeline = Pipeline(tenant_id=tenant.id, name=payload.name)
    db.add(pipeline)
    db.flush()

    for index, stage_name in enumerate(payload.stages):
        db.add(
            PipelineStage(
                tenant_id=tenant.id,
                pipeline_id=pipeline.id,
                name=stage_name,
                sort_order=index,
            )
        )

    db.commit()
    db.refresh(pipeline)
    return pipeline


@router.get("/pipelines", response_model=list[PipelineResponse])
def list_pipelines(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[Pipeline]:
    return db.query(Pipeline).filter(Pipeline.tenant_id == tenant.id).order_by(Pipeline.created_at.desc()).all()


@router.post("/deals", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
def create_deal(
    payload: DealCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> Deal:
    _get_for_tenant(db, Company, tenant.id, payload.company_id)
    _get_for_tenant(db, PipelineStage, tenant.id, payload.stage_id)
    if payload.lead_id is not None:
        lead = _get_for_tenant(db, Lead, tenant.id, payload.lead_id)
        if lead.company_id != payload.company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead belongs to another company")

    deal = Deal(tenant_id=tenant.id, **payload.model_dump())
    db.add(deal)
    db.flush()
    ActivityService(db).create(
        tenant_id=tenant.id,
        created_by=tenant.user_id,
        company_id=deal.company_id,
        deal_id=deal.id,
        activity_type="SYSTEM",
        title="Deal created",
        description=deal.title,
        metadata={"deal_id": str(deal.id), "amount": float(deal.amount or 0)},
        commit=False,
    )
    db.commit()
    db.refresh(deal)
    return deal


@router.get("/deals", response_model=list[DealResponse])
def list_deals(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[Deal]:
    return db.query(Deal).filter(Deal.tenant_id == tenant.id).order_by(Deal.created_at.desc()).all()


@router.post("/next-actions", response_model=NextActionResponse, status_code=status.HTTP_201_CREATED)
def create_next_action(
    payload: NextActionCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> NextAction:
    company = _get_for_tenant(db, Company, tenant.id, payload.company_id)
    if payload.deal_id is not None:
        deal = _get_for_tenant(db, Deal, tenant.id, payload.deal_id)
        if deal.company_id != payload.company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deal belongs to another company")
    if payload.contact_id is not None:
        contact = _get_for_tenant(db, Contact, tenant.id, payload.contact_id)
        if contact.company_id != payload.company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contact belongs to another company")

    next_action = NextAction(
        tenant_id=tenant.id,
        assigned_to_id=payload.assigned_to_id or tenant.user_id,
        **payload.model_dump(exclude={"assigned_to_id"}),
    )
    db.add(next_action)
    db.flush()

    company.next_action_id = next_action.id
    if next_action.deal_id:
        deal = _get_for_tenant(db, Deal, tenant.id, next_action.deal_id)
        deal.next_action_id = next_action.id
        deal.next_step = next_action.title

    ActivityService(db).create(
        tenant_id=tenant.id,
        created_by=tenant.user_id,
        company_id=next_action.company_id,
        deal_id=next_action.deal_id,
        contact_id=next_action.contact_id,
        activity_type="AI_ACTION" if next_action.source == "ai" else "TASK",
        title="Next action created",
        description=next_action.title,
        metadata={"next_action_id": str(next_action.id), "priority": next_action.priority},
        commit=False,
    )
    db.commit()
    db.refresh(next_action)
    return next_action


@router.get("/next-actions", response_model=list[NextActionResponse])
def list_next_actions(
    company_id: UUID | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[NextAction]:
    query = db.query(NextAction).filter(NextAction.tenant_id == tenant.id)
    if company_id is not None:
        query = query.filter(NextAction.company_id == company_id)
    if status_filter is not None:
        query = query.filter(NextAction.status == status_filter)
    return query.order_by(NextAction.created_at.desc()).all()


@router.patch("/next-actions/{next_action_id}/done", response_model=NextActionResponse)
def set_next_action_done(
    next_action_id: UUID,
    payload: NextActionDoneRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> NextAction:
    next_action = _get_for_tenant(db, NextAction, tenant.id, next_action_id)
    next_action.status = "done" if payload.is_done else "open"
    next_action.completed_at = datetime.now(timezone.utc) if payload.is_done else None
    company = _get_for_tenant(db, Company, tenant.id, next_action.company_id)
    deal = (
        _get_for_tenant(db, Deal, tenant.id, next_action.deal_id)
        if next_action.deal_id
        else None
    )
    if payload.is_done:
        if company.next_action_id == next_action.id:
            company.next_action_id = None
        if deal and deal.next_action_id == next_action.id:
            deal.next_action_id = None
    else:
        company.next_action_id = next_action.id
        if deal:
            deal.next_action_id = next_action.id
            deal.next_step = next_action.title
    ActivityService(db).create(
        tenant_id=tenant.id,
        created_by=tenant.user_id,
        company_id=next_action.company_id,
        deal_id=next_action.deal_id,
        contact_id=next_action.contact_id,
        activity_type="TASK",
        title="Next action completed" if payload.is_done else "Next action reopened",
        description=next_action.title,
        metadata={"next_action_id": str(next_action.id), "done": payload.is_done},
        commit=False,
    )
    db.commit()
    db.refresh(next_action)
    return next_action


@router.patch("/deals/{deal_id}/move", response_model=DealResponse)
def move_deal(
    deal_id: UUID,
    payload: DealMoveRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> Deal:
    deal = _get_for_tenant(db, Deal, tenant.id, deal_id)
    old_stage_id = deal.stage_id
    new_stage = _get_for_tenant(db, PipelineStage, tenant.id, payload.stage_id)

    deal.stage_id = payload.stage_id
    ActivityService(db).create(
        tenant_id=tenant.id,
        created_by=tenant.user_id,
        company_id=deal.company_id,
        deal_id=deal.id,
        activity_type="DEAL_STAGE_CHANGED",
        title="Этап сделки изменён",
        description=f"{deal.title}: новый этап — {stage_label_ru(new_stage.name)}",
        metadata={"old_stage_id": str(old_stage_id), "new_stage_id": str(payload.stage_id)},
        commit=False,
    )
    db.commit()
    db.refresh(deal)
    return deal


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> Task:
    _get_for_tenant(db, Company, tenant.id, payload.company_id)
    if payload.deal_id is not None:
        deal = _get_for_tenant(db, Deal, tenant.id, payload.deal_id)
        if deal.company_id != payload.company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deal belongs to another company")

    task = Task(tenant_id=tenant.id, assigned_to_id=tenant.user_id, **payload.model_dump())
    db.add(task)
    db.flush()
    ActivityService(db).create(
        tenant_id=tenant.id,
        created_by=tenant.user_id,
        company_id=task.company_id,
        deal_id=task.deal_id,
        activity_type="TASK",
        title="Task created",
        description=task.title,
        metadata={"task_id": str(task.id)},
        commit=False,
    )
    db.commit()
    db.refresh(task)
    return task


@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[Task]:
    return db.query(Task).filter(Task.tenant_id == tenant.id).order_by(Task.created_at.desc()).all()


@router.patch("/tasks/{task_id}/done", response_model=TaskResponse)
def set_task_done(
    task_id: UUID,
    payload: TaskDoneRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> Task:
    task = _get_for_tenant(db, Task, tenant.id, task_id)
    task.done_at = datetime.now(timezone.utc) if payload.is_done else None
    task.status = "done" if payload.is_done else "open"
    ActivityService(db).create(
        tenant_id=tenant.id,
        created_by=tenant.user_id,
        company_id=task.company_id,
        deal_id=task.deal_id,
        activity_type="TASK",
        title="Task completed" if payload.is_done else "Task reopened",
        description=task.title,
        metadata={"task_id": str(task.id), "done": payload.is_done},
        commit=False,
    )
    db.commit()
    db.refresh(task)
    return task


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: NoteCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> Note:
    _get_for_tenant(db, Company, tenant.id, payload.company_id)
    if payload.lead_id is not None:
        lead = _get_for_tenant(db, Lead, tenant.id, payload.lead_id)
        if lead.company_id != payload.company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead belongs to another company")
    if payload.deal_id is not None:
        deal = _get_for_tenant(db, Deal, tenant.id, payload.deal_id)
        if deal.company_id != payload.company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deal belongs to another company")

    note = Note(tenant_id=tenant.id, author_id=tenant.user_id, **payload.model_dump())
    db.add(note)
    db.flush()
    ActivityService(db).create(
        tenant_id=tenant.id,
        created_by=tenant.user_id,
        company_id=note.company_id,
        deal_id=note.deal_id,
        activity_type="NOTE",
        title="Note added",
        description=note.text,
        metadata={"note_id": str(note.id), "lead_id": str(note.lead_id) if note.lead_id else None},
        commit=False,
    )
    db.commit()
    db.refresh(note)
    return note


@router.get("/notes", response_model=list[NoteResponse])
def list_notes(
    lead_id: UUID | None = None,
    deal_id: UUID | None = None,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[Note]:
    query = db.query(Note).filter(Note.tenant_id == tenant.id)
    if lead_id is not None:
        query = query.filter(Note.lead_id == lead_id)
    if deal_id is not None:
        query = query.filter(Note.deal_id == deal_id)
    return query.order_by(Note.created_at.desc()).all()


def _company_response(company: Company, owner: User | None, source: str | None) -> CompanyResponse:
    return CompanyResponse(
        id=company.id,
        name=company.name,
        website=company.website,
        industry=company.industry,
        description=company.description,
        status=company.status,
        status_label=_status_label(company.status),
        company_type=company.company_type or company.industry,
        health_score=company.health_score,
        client_since=company.client_since or company.created_at,
        source=source,
        owner=_owner_response(owner),
        next_action_id=company.next_action_id,
        created_at=company.created_at,
    )


def _owner_response(owner: User | None) -> OwnerResponse | None:
    if owner is None:
        return None
    return OwnerResponse(
        id=owner.id,
        name=owner.full_name,
        avatar_url=owner.avatar_url,
        initials=_initials(owner.full_name),
    )


def _contact_response(contact: Contact) -> ContactResponse:
    return ContactResponse(
        id=contact.id,
        company_id=contact.company_id,
        name=contact.name,
        phone=contact.phone,
        email=contact.email,
        company_name=contact.company_name,
        role=contact.role,
        actions={
            "call": bool(contact.can_call and contact.phone),
            "email": bool(contact.can_email and contact.email),
            "more": bool(contact.can_open_more),
        },
        created_at=contact.created_at,
    )


def _deal_response(deal: Deal) -> DealResponse:
    return DealResponse(
        id=deal.id,
        company_id=deal.company_id,
        title=deal.title,
        amount=float(deal.amount) if deal.amount is not None else None,
        status=deal.status,
        lead_id=deal.lead_id,
        stage_id=deal.stage_id,
        probability=deal.probability,
        expected_close_date=deal.expected_close_date,
        expected_next_event=deal.expected_next_event,
        next_step=deal.next_step,
        risk_level=deal.risk_level,
        forecast_category=deal.forecast_category,
        owner_id=deal.owner_id,
        next_action_id=deal.next_action_id,
        age_days=_age_days(deal.created_at),
        created_at=deal.created_at,
    )


def _next_action_dict(next_action: NextAction) -> dict:
    return {
        "id": str(next_action.id),
        "company_id": str(next_action.company_id),
        "deal_id": str(next_action.deal_id) if next_action.deal_id else None,
        "contact_id": str(next_action.contact_id) if next_action.contact_id else None,
        "assigned_to_id": str(next_action.assigned_to_id) if next_action.assigned_to_id else None,
        "title": next_action.title,
        "description": next_action.description,
        "source": next_action.source,
        "status": next_action.status,
        "priority": next_action.priority,
        "due_at": next_action.due_at.isoformat() if next_action.due_at else None,
        "completed_at": next_action.completed_at.isoformat() if next_action.completed_at else None,
        "created_at": next_action.created_at.isoformat(),
    }


def _resolve_company_next_action(db: Session, tenant_id: UUID, company: Company) -> NextAction | None:
    if company.next_action_id:
        action = (
            db.query(NextAction)
            .filter(
                NextAction.id == company.next_action_id,
                NextAction.tenant_id == tenant_id,
                NextAction.status == "open",
            )
            .one_or_none()
        )
        if action is not None:
            return action
    return (
        db.query(NextAction)
        .filter(
            NextAction.tenant_id == tenant_id,
            NextAction.company_id == company.id,
            NextAction.status == "open",
        )
        .order_by(NextAction.due_at.asc().nullslast(), NextAction.created_at.desc())
        .first()
    )


def _activity_workspace_response(activity, author: User | None) -> dict:
    activity_type = _normalize_activity_type(activity.type, activity.channel)
    return {
        "id": str(activity.id),
        "type": activity.type,
        "activity_type": activity_type,
        "activity_icon": _activity_icon(activity_type),
        "channel": activity.channel or _channel_from_type(activity_type),
        "title": activity.title,
        "description": activity.description,
        "author_name": author.full_name if author else None,
        "created_at": activity.created_at.isoformat(),
        "metadata": json.loads(activity.metadata_json or "{}"),
    }


def _age_days(value: datetime) -> int:
    created_at = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - created_at).days)


def _file_response(file: CompanyFile) -> dict:
    return {
        "id": str(file.id),
        "name": file.name,
        "file_type": file.file_type,
        "mime_type": file.mime_type,
        "file_size": file.file_size,
        "uploaded_at": file.created_at.isoformat(),
        "download_url": file.download_url or f"/files/{file.id}/download",
    }


def _knowledge_document_response(document: KnowledgeDocument) -> dict:
    return {
        "id": str(document.id),
        "title": document.title,
        "source_type": document.source_type,
        "visibility": document.visibility,
        "company_id": str(document.company_id) if document.company_id else None,
        "deal_id": str(document.deal_id) if document.deal_id else None,
        "file_id": str(document.file_id) if document.file_id else None,
        "created_at": document.created_at.isoformat(),
        "chunks_count": len(document.chunks),
        "download_url": f"/knowledge/documents/{document.id}/download" if document.file_id else None,
        "extraction_method": document.extraction_method,
        "source_pages": document.source_pages,
    }


def _company_file_response(file: CompanyFile) -> CompanyFileResponse:
    return CompanyFileResponse(
        id=file.id,
        company_id=file.company_id,
        deal_id=file.deal_id,
        contact_id=file.contact_id,
        activity_id=file.activity_id,
        uploaded_by_id=file.uploaded_by_id,
        name=file.name,
        file_type=file.file_type,
        mime_type=file.mime_type,
        file_size=file.file_size,
        storage_key=file.storage_key,
        download_url=file.download_url or f"/sales/files/{file.id}/download",
        created_at=file.created_at,
    )


def _customer_insight_response(insight: CustomerInsight) -> CustomerInsightResponse:
    return CustomerInsightResponse(
        id=insight.id,
        company_id=insight.company_id,
        health_score=insight.health_score,
        health_label=insight.health_label,
        health_trend=insight.health_trend,
        risk_level=insight.risk_level,
        success_chance=insight.success_chance,
        success_chance_delta=insight.success_chance_delta,
        ai_recommendations=json.loads(insight.ai_recommendations_json or "[]"),
        updated_at=insight.updated_at,
    )


def _health_response(insight: CustomerInsight | None, contacts: list[Contact], deals: list[Deal]) -> dict:
    fallback_score = min(98, 70 + len(contacts) * 4 + len(deals) * 6)
    if insight is None:
        return {
            "score": fallback_score,
            "label": "Хороший" if fallback_score >= 70 else "Средний",
            "trend": "up",
            "risk_level": None,
            "success_chance": None,
            "success_chance_delta": None,
            "ai_recommendations": [],
        }
    return {
        "score": insight.health_score if insight.health_score is not None else fallback_score,
        "label": insight.health_label,
        "trend": insight.health_trend,
        "risk_level": insight.risk_level,
        "success_chance": insight.success_chance,
        "success_chance_delta": insight.success_chance_delta,
        "ai_recommendations": json.loads(insight.ai_recommendations_json or "[]"),
    }


def _company_source(company: Company, db: Session, tenant_id: UUID) -> str | None:
    lead = (
        db.query(Lead)
        .filter(Lead.tenant_id == tenant_id, Lead.company_id == company.id, Lead.source.isnot(None))
        .order_by(Lead.created_at.asc())
        .first()
    )
    return lead.source if lead else None


def _metadata_value(value) -> str | int | float | bool | None:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _normalize_activity_type(activity_type: str, channel: str | None = None) -> str:
    value = (channel or activity_type or "").lower()
    if "call" in value or "phone" in value:
        return "call"
    if "email" in value or "mail" in value:
        return "email"
    if "meeting" in value or "meet" in value:
        return "meeting"
    if "message" in value or "comment" in value or "note" in value:
        return "message"
    if "task" in value:
        return "task"
    if "deal" in value:
        return "deal"
    return "system"


def _activity_icon(activity_type: str) -> str:
    return {
        "call": "phone",
        "email": "mail",
        "meeting": "calendar",
        "message": "message",
        "task": "task",
        "deal": "check",
    }.get(activity_type, "building")


def _channel_from_type(activity_type: str) -> str | None:
    return {
        "call": "Call",
        "email": "Email",
        "meeting": "Meeting",
        "message": "Message",
    }.get(activity_type)


def _channel_summary(activities: list[dict]) -> str | None:
    channels = []
    for activity in activities:
        channel = activity.get("channel")
        if channel and channel not in channels:
            channels.append(channel)
    return ", ".join(channels) if channels else None


def _status_label(status_value: str) -> str:
    return {
        "active": "Активный",
        "inactive": "Неактивный",
        "archived": "Архив",
    }.get(status_value, status_value)


def _initials(name: str) -> str:
    parts = [part for part in name.split() if part]
    return "".join(part[0] for part in parts[:2]).upper()


def _get_for_tenant(db: Session, model, tenant_id: UUID, entity_id: UUID):
    entity = db.query(model).filter(model.id == entity_id, model.tenant_id == tenant_id).one_or_none()
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{model.__name__} not found")
    return entity
