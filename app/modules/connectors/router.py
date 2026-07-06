import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentTenant, get_current_tenant
from app.modules.connectors.models import ConnectorAccount, ConnectorSyncRun
from app.modules.connectors.schemas import (
    ConnectorAccountCreate,
    ConnectorAccountResponse,
    ConnectorDefinitionResponse,
    ConnectorSyncResponse,
    CsvExportResponse,
    CsvImportRequest,
)
from app.modules.connectors.service import ConnectorService


router = APIRouter()


@router.get("/definitions", response_model=list[ConnectorDefinitionResponse])
def definitions(db: Session = Depends(get_db)) -> list[ConnectorDefinitionResponse]:
    service = ConnectorService(db)
    return [ConnectorDefinitionResponse(**connector.__dict__) for connector in service.definitions()]


@router.post("/accounts", response_model=ConnectorAccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: ConnectorAccountCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> ConnectorAccountResponse:
    service = ConnectorService(db)
    try:
        account = service.create_account(
            tenant_id=tenant.id,
            connector_code=payload.connector_code,
            title=payload.title,
            credentials=payload.credentials,
            settings=payload.settings,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return _account_response(account)


@router.get("/accounts", response_model=list[ConnectorAccountResponse])
def list_accounts(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[ConnectorAccountResponse]:
    service = ConnectorService(db)
    return [_account_response(account) for account in service.list_accounts(tenant.id)]


@router.post("/accounts/{account_id}/csv/import", response_model=ConnectorSyncResponse)
def import_csv(
    account_id: UUID,
    payload: CsvImportRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> ConnectorSyncResponse:
    service = ConnectorService(db)
    return _run_response(service.import_csv_leads(tenant.id, account_id, payload.csv_text))


@router.get("/csv/export", response_model=CsvExportResponse)
def export_csv(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> CsvExportResponse:
    service = ConnectorService(db)
    return CsvExportResponse(filename="leads.csv", csv_text=service.export_csv_leads(tenant.id))


@router.get("/runs", response_model=list[ConnectorSyncResponse])
def list_runs(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[ConnectorSyncResponse]:
    service = ConnectorService(db)
    return [_run_response(run) for run in service.list_runs(tenant.id)]


def _account_response(account: ConnectorAccount) -> ConnectorAccountResponse:
    return ConnectorAccountResponse(
        id=account.id,
        connector_code=account.connector_code,
        title=account.title,
        status=account.status,
        settings=json.loads(account.settings_json),
        last_sync_at=account.last_sync_at,
        created_at=account.created_at,
    )


def _run_response(run: ConnectorSyncRun) -> ConnectorSyncResponse:
    return ConnectorSyncResponse(
        id=run.id,
        account_id=run.account_id,
        direction=run.direction,
        status=run.status,
        created_count=run.created_count,
        updated_count=run.updated_count,
        failed_count=run.failed_count,
        message=run.message,
        created_at=run.created_at,
    )

