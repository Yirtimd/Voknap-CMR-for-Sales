from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentTenant, get_current_tenant
from app.modules.knowledge.models import KnowledgeDocument
from app.modules.knowledge.schemas import (
    AskRequest,
    AskResponse,
    CitationResponse,
    DocumentCreate,
    DocumentResponse,
    KnowledgeScope,
    SearchRequest,
    SearchResultResponse,
)
from app.modules.knowledge.service import KnowledgeService


router = APIRouter()


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> DocumentResponse:
    service = KnowledgeService(db)
    try:
        document = service.create_document(
            tenant_id=tenant.id,
            title=payload.title,
            text=payload.text,
            source_type=payload.source_type,
            company_id=payload.company_id,
            deal_id=payload.deal_id,
            file_id=payload.file_id,
            visibility=payload.visibility,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return _document_response(document)


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    scope: KnowledgeScope = "global",
    company_id: UUID | None = None,
    deal_id: UUID | None = None,
    include_global: bool = False,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[DocumentResponse]:
    service = KnowledgeService(db)
    try:
        documents = service.list_documents(
            tenant.id,
            scope=scope,
            company_id=company_id,
            deal_id=deal_id,
            include_global=include_global,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return [_document_response(document) for document in documents]


@router.post("/companies/{company_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_company_document(
    company_id: UUID,
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> DocumentResponse:
    service = KnowledgeService(db)
    try:
        document = service.create_document(
            tenant_id=tenant.id,
            title=payload.title,
            text=payload.text,
            source_type=payload.source_type,
            company_id=company_id,
            deal_id=payload.deal_id,
            file_id=payload.file_id,
            visibility="deal" if payload.deal_id else "company",
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return _document_response(document)


@router.get("/companies/{company_id}/documents", response_model=list[DocumentResponse])
def list_company_documents(
    company_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[DocumentResponse]:
    service = KnowledgeService(db)
    try:
        documents = service.list_documents(tenant.id, scope="company", company_id=company_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return [_document_response(document) for document in documents]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> DocumentResponse:
    document = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.id == document_id, KnowledgeDocument.tenant_id == tenant.id)
        .one_or_none()
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _document_response(document)


@router.post("/search", response_model=list[SearchResultResponse])
def search(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[SearchResultResponse]:
    service = KnowledgeService(db)
    try:
        results = service.search(
            tenant_id=tenant.id,
            query=payload.query,
            limit=payload.limit,
            scope=payload.scope,
            company_id=payload.company_id,
            deal_id=payload.deal_id,
            include_global=payload.include_global,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return [
        SearchResultResponse(
            chunk_id=item.chunk.id,
            document_id=item.document.id,
            document_title=item.document.title,
            document_scope=item.document.visibility,
            company_id=item.document.company_id,
            deal_id=item.document.deal_id,
            text=item.chunk.text,
            score=item.score,
            chunk_index=item.chunk.chunk_index,
        )
        for item in results
    ]


@router.post("/ask", response_model=AskResponse)
def ask(
    payload: AskRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> AskResponse:
    service = KnowledgeService(db)
    try:
        answer, ranked_chunks = service.answer(
            tenant_id=tenant.id,
            user_id=tenant.user_id,
            question=payload.question,
            limit=payload.limit,
            scope=payload.scope,
            company_id=payload.company_id,
            deal_id=payload.deal_id,
            include_global=payload.include_global,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return AskResponse(
        answer=answer,
        citations=[
            CitationResponse(
                chunk_id=item.chunk.id,
                document_id=item.document.id,
                document_title=item.document.title,
                document_scope=item.document.visibility,
                company_id=item.document.company_id,
                deal_id=item.document.deal_id,
                chunk_index=item.chunk.chunk_index,
                text=item.chunk.text,
                score=item.score,
            )
            for item in ranked_chunks
        ],
        scope=payload.scope,
        company_id=payload.company_id,
        deal_id=payload.deal_id,
        include_global=payload.include_global,
    )


def _document_response(document: KnowledgeDocument) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        company_id=document.company_id,
        deal_id=document.deal_id,
        file_id=document.file_id,
        title=document.title,
        source_type=document.source_type,
        visibility=document.visibility,
        status=document.status,
        created_at=document.created_at,
        chunks_count=len(document.chunks),
    )
