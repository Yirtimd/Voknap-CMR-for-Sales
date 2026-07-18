import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentTenant, get_current_tenant
from app.core.rbac import Permission, require_permission
from app.modules.connectors.models import ConnectorAccount, ConnectorSyncRun
from app.modules.connectors.schemas import (
    ConnectorAccountCreate,
    ConnectorAccountResponse,
    ConnectorDefinitionResponse,
    ConnectorSyncRequest,
    ConnectorSyncResponse,
    CsvExportResponse,
    CsvImportRequest,
)
from app.modules.connectors.service import ConnectorService


router = APIRouter()


@router.get("/definitions", response_model=list[ConnectorDefinitionResponse])
def definitions(
    db: Session = Depends(get_db),
    _tenant: CurrentTenant = Depends(get_current_tenant),
) -> list[ConnectorDefinitionResponse]:
    service = ConnectorService(db)
    return [ConnectorDefinitionResponse(**connector.__dict__) for connector in service.definitions()]


@router.post("/accounts", response_model=ConnectorAccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: ConnectorAccountCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
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
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> list[ConnectorAccountResponse]:
    service = ConnectorService(db)
    return [_account_response(account) for account in service.list_accounts(tenant.id)]


@router.post("/accounts/{account_id}/csv/import", response_model=ConnectorSyncResponse)
def import_csv(
    account_id: UUID,
    payload: CsvImportRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> ConnectorSyncResponse:
    service = ConnectorService(db)
    return _run_response(service.import_csv_leads(tenant.id, account_id, payload.csv_text))


@router.post("/accounts/{account_id}/sync", response_model=ConnectorSyncResponse)
def sync_account(
    account_id: UUID,
    payload: ConnectorSyncRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> ConnectorSyncResponse:
    service = ConnectorService(db)
    return _run_response(service.sync_account(tenant.id, account_id, payload.payload))


@router.post("/runs/{run_id}/retry", response_model=ConnectorSyncResponse)
def retry_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> ConnectorSyncResponse:
    service = ConnectorService(db)
    run = service.retry_run(tenant.id, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector run not found")
    return _run_response(run)


@router.get("/csv/export", response_model=CsvExportResponse)
def export_csv(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.DATA_EXPORT)),
) -> CsvExportResponse:
    service = ConnectorService(db)
    return CsvExportResponse(filename="leads.csv", csv_text=service.export_csv_leads(tenant.id))


@router.get("/runs", response_model=list[ConnectorSyncResponse])
def list_runs(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> list[ConnectorSyncResponse]:
    service = ConnectorService(db)
    return [_run_response(run) for run in service.list_runs(tenant.id)]


def _account_response(account: ConnectorAccount) -> ConnectorAccountResponse:
    return ConnectorAccountResponse(
        id=account.id,
        connector_code=account.connector_code,
        title=account.title,
        status=account.status,
        credentials_encrypted=account.credentials_encrypted,
        settings=json.loads(account.settings_json),
        sync_cursor=account.sync_cursor,
        last_sync_at=account.last_sync_at,
        created_at=account.created_at,
    )


def _run_response(run: ConnectorSyncRun) -> ConnectorSyncResponse:
    return ConnectorSyncResponse(
        id=run.id,
        account_id=run.account_id,
        direction=run.direction,
        status=run.status,
        job_type=run.job_type,
        attempt=run.attempt,
        max_attempts=run.max_attempts,
        next_retry_at=run.next_retry_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_count=run.created_count,
        updated_count=run.updated_count,
        failed_count=run.failed_count,
        message=run.message,
        error_code=run.error_code,
        error_details=json.loads(run.error_details_json or "{}"),
        created_at=run.created_at,
    )
