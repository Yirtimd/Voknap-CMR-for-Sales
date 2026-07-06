from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentTenant, get_current_tenant
from app.modules.activity.service import ActivityService
from app.modules.sales.models import Company, Contact, Deal, Lead, Note, Pipeline, PipelineStage, Task
from app.modules.sales.schemas import (
    CompanyCreate,
    CompanyResponse,
    CompanyWorkspaceResponse,
    ContactCreate,
    ContactResponse,
    DealCreate,
    DealMoveRequest,
    DealResponse,
    LeadCreate,
    LeadResponse,
    NoteCreate,
    NoteResponse,
    PipelineCreate,
    PipelineResponse,
    TaskCreate,
    TaskDoneRequest,
    TaskResponse,
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
    related_activities = ActivityService(db).list(tenant_id=tenant.id, company_id=company.id, limit=80)
    open_tasks = [task for task in tasks if task.done_at is None]
    total_amount = sum(float(deal.amount or 0) for deal in deals)
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
        company=CompanyResponse.model_validate(company),
        overview={
            "contacts_count": len(contacts),
            "deals_count": len(deals),
            "open_tasks_count": len(open_tasks),
            "pipeline_amount": total_amount,
        },
        contacts=contacts,
        deals=deals,
        tasks=tasks,
        activities=[
            {
                "id": str(activity.id),
                "type": activity.type,
                "title": activity.title,
                "description": activity.description,
                "created_at": activity.created_at.isoformat(),
            }
            for activity in related_activities
        ],
        ai_summary=ai_summary,
        ai_insights=ai_insights,
    )


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
        title="Deal stage changed",
        description=f"{deal.title} moved to {new_stage.name}",
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


def _get_for_tenant(db: Session, model, tenant_id: UUID, entity_id: UUID):
    entity = db.query(model).filter(model.id == entity_id, model.tenant_id == tenant_id).one_or_none()
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{model.__name__} not found")
    return entity
