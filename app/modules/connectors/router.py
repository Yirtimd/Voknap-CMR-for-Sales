import json
import secrets
from datetime import datetime
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import CurrentTenant, get_current_tenant
from app.core.rbac import Permission, require_permission
from app.modules.connectors.api_keys import create_api_key
from app.modules.connectors.importers import (
    ImportValidationError,
    apply_mapping,
    parse_import_file,
    suggest_mapping,
)
from app.modules.connectors.jobs import (
    IntegrationJobService,
    validate_webhook_url,
)
from app.modules.connectors.models import (
    ConnectorAccount,
    ConnectorSyncRun,
    IntegrationJob,
    PublicApiKey,
    WebhookEndpoint,
)
from app.modules.connectors.oauth import complete_authorization, create_authorization_url
from app.modules.connectors.schemas import (
    CalendarEventCreateRequest,
    ConnectorAccountCreate,
    ConnectorAccountResponse,
    ConnectorDefinitionResponse,
    ConnectorSyncRequest,
    ConnectorSyncResponse,
    CsvExportResponse,
    CsvImportRequest,
    EmailSendRequest,
    ImportEnqueueResponse,
    ImportPreviewResponse,
    IntegrationJobResponse,
    OAuthStartResponse,
    PublicApiKeyCreate,
    PublicApiKeyResponse,
    WebhookEndpointCreate,
    WebhookEndpointResponse,
    WebhookTestRequest,
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


@router.post("/accounts/{account_id}/sync", response_model=IntegrationJobResponse)
def sync_account(
    account_id: UUID,
    payload: ConnectorSyncRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> IntegrationJobResponse:
    account = (
        db.query(ConnectorAccount)
        .filter(ConnectorAccount.tenant_id == tenant.id, ConnectorAccount.id == account_id)
        .one_or_none()
    )
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector account not found")
    if account.status != "connected":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connector is not connected")
    job_types = {
        "email": "email.sync",
        "google_calendar": "calendar.sync",
        "microsoft_calendar": "calendar.sync",
    }
    job_type = job_types.get(account.connector_code)
    if not job_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connector has no sync operation")
    key = payload.idempotency_key or f"{job_type}:{account.id}:{datetime.now().isoformat()}"
    job = IntegrationJobService(db).enqueue(
        tenant_id=tenant.id,
        account_id=account.id,
        job_type=job_type,
        idempotency_key=key,
        payload=payload.payload,
        created_by_id=tenant.user_id,
    )
    return _job_response(job)


@router.post("/accounts/{account_id}/email/send", response_model=IntegrationJobResponse)
def send_email(
    account_id: UUID,
    payload: EmailSendRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> IntegrationJobResponse:
    job = IntegrationJobService(db).enqueue(
        tenant_id=tenant.id,
        account_id=account_id,
        job_type="email.send",
        idempotency_key=payload.idempotency_key,
        payload=payload.model_dump(exclude={"idempotency_key"}),
        created_by_id=tenant.user_id,
    )
    return _job_response(job)


@router.post("/accounts/{account_id}/calendar/events", response_model=IntegrationJobResponse)
def create_calendar_item(
    account_id: UUID,
    payload: CalendarEventCreateRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> IntegrationJobResponse:
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="ends_at must be after starts_at")
    data = payload.model_dump(mode="json", exclude={"idempotency_key"})
    job = IntegrationJobService(db).enqueue(
        tenant_id=tenant.id,
        account_id=account_id,
        job_type="calendar.create",
        idempotency_key=payload.idempotency_key,
        payload=data,
        created_by_id=tenant.user_id,
    )
    return _job_response(job)


@router.post("/accounts/{account_id}/oauth/start", response_model=OAuthStartResponse)
def start_oauth(
    account_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> OAuthStartResponse:
    account = (
        db.query(ConnectorAccount)
        .filter(ConnectorAccount.tenant_id == tenant.id, ConnectorAccount.id == account_id)
        .one_or_none()
    )
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector account not found")
    try:
        return OAuthStartResponse(
            authorization_url=create_authorization_url(account, tenant.user_id)
        )
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/oauth/{provider}/callback", include_in_schema=False)
def oauth_callback(
    provider: str,
    code: str,
    state: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        complete_authorization(db, provider, code, state)
    except ValueError as error:
        return RedirectResponse(
            f"{settings.frontend_url.rstrip('/')}/settings?"
            + urlencode({"integration_error": str(error)}),
            status_code=status.HTTP_302_FOUND,
        )
    return RedirectResponse(
        f"{settings.frontend_url.rstrip('/')}/settings?integration=connected",
        status_code=status.HTTP_302_FOUND,
    )


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> None:
    account = (
        db.query(ConnectorAccount)
        .filter(ConnectorAccount.tenant_id == tenant.id, ConnectorAccount.id == account_id)
        .one_or_none()
    )
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector account not found")
    account.status = "disconnected"
    account.credentials_json = ConnectorService(db)._encrypt_credentials({})
    account.sync_cursor = None
    db.commit()


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


@router.get("/jobs", response_model=list[IntegrationJobResponse])
def list_jobs(
    job_status: str | None = None,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> list[IntegrationJobResponse]:
    return [
        _job_response(job)
        for job in IntegrationJobService(db).list_jobs(tenant.id, job_status)
    ]


@router.post("/jobs/{job_id}/replay", response_model=IntegrationJobResponse)
def replay_dead_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> IntegrationJobResponse:
    job = IntegrationJobService(db).replay(tenant.id, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration job not found")
    return _job_response(job)


@router.post("/imports/preview", response_model=ImportPreviewResponse)
async def preview_import(
    file: UploadFile = File(...),
    _tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> ImportPreviewResponse:
    content = await file.read(settings.integration_import_max_bytes + 1)
    try:
        headers, rows = parse_import_file(file.filename or "import.csv", content)
    except ImportValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return ImportPreviewResponse(
        filename=file.filename or "import.csv",
        headers=headers,
        rows=rows[:20],
        suggested_mapping=suggest_mapping(headers),
        total_rows=len(rows),
    )


@router.post("/imports", response_model=ImportEnqueueResponse)
async def enqueue_import(
    file: UploadFile = File(...),
    mapping_json: str = Form(...),
    idempotency_key: str = Form(..., min_length=8, max_length=255),
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> ImportEnqueueResponse:
    content = await file.read(settings.integration_import_max_bytes + 1)
    try:
        _headers, rows = parse_import_file(file.filename or "import.csv", content)
        mapping = json.loads(mapping_json)
        if not isinstance(mapping, dict):
            raise ImportValidationError("Mapping must be an object")
        mapped, errors = apply_mapping(rows, mapping)
    except (ImportValidationError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    job = IntegrationJobService(db).enqueue(
        tenant_id=tenant.id,
        job_type="contacts.import",
        idempotency_key=idempotency_key,
        payload={"filename": file.filename, "rows": mapped},
        created_by_id=tenant.user_id,
    )
    return ImportEnqueueResponse(
        job=_job_response(job),
        accepted_rows=len(mapped),
        validation_errors=errors[:100],
    )


@router.post("/webhooks", response_model=WebhookEndpointResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    payload: WebhookEndpointCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> WebhookEndpointResponse:
    if settings.secret_key == "change-me-in-production" or len(settings.secret_key) < 32:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set a unique SECRET_KEY of at least 32 characters before creating webhooks",
        )
    try:
        validate_webhook_url(payload.url)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    allowed_events = {"lead.created", "integration.test"}
    invalid = sorted(set(payload.event_types) - allowed_events)
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported events: {', '.join(invalid)}",
        )
    secret = secrets.token_urlsafe(32)
    endpoint = WebhookEndpoint(
        tenant_id=tenant.id,
        title=payload.title,
        url=payload.url,
        event_types_json=json.dumps(sorted(set(payload.event_types))),
        secret_encrypted=ConnectorService(db)._encrypt_secret(secret),
        created_by_id=tenant.user_id,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return _webhook_response(endpoint, secret)


@router.get("/webhooks", response_model=list[WebhookEndpointResponse])
def list_webhooks(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> list[WebhookEndpointResponse]:
    rows = (
        db.query(WebhookEndpoint)
        .filter(WebhookEndpoint.tenant_id == tenant.id)
        .order_by(WebhookEndpoint.created_at.desc())
        .all()
    )
    return [_webhook_response(item) for item in rows]


@router.post("/webhooks/{endpoint_id}/test", response_model=IntegrationJobResponse)
def test_webhook(
    endpoint_id: UUID,
    payload: WebhookTestRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> IntegrationJobResponse:
    endpoint = (
        db.query(WebhookEndpoint)
        .filter(WebhookEndpoint.tenant_id == tenant.id, WebhookEndpoint.id == endpoint_id)
        .one_or_none()
    )
    if not endpoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    event = {
        "id": payload.idempotency_key,
        "type": "integration.test",
        "created_at": datetime.now().isoformat(),
        "tenant_id": str(tenant.id),
        "data": {"message": "Voknap CRM webhook test"},
    }
    job = IntegrationJobService(db).enqueue(
        tenant_id=tenant.id,
        job_type="webhook.deliver",
        idempotency_key=f"webhook:{endpoint.id}:{payload.idempotency_key}",
        payload={"endpoint_id": str(endpoint.id), "event": event},
        created_by_id=tenant.user_id,
    )
    return _job_response(job)


@router.delete("/webhooks/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def disable_webhook(
    endpoint_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> None:
    endpoint = (
        db.query(WebhookEndpoint)
        .filter(WebhookEndpoint.tenant_id == tenant.id, WebhookEndpoint.id == endpoint_id)
        .one_or_none()
    )
    if not endpoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    endpoint.is_active = False
    db.commit()


@router.post("/api-keys", response_model=PublicApiKeyResponse, status_code=status.HTTP_201_CREATED)
def issue_api_key(
    payload: PublicApiKeyCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> PublicApiKeyResponse:
    try:
        key, raw_key = create_api_key(
            db,
            tenant_id=tenant.id,
            title=payload.title,
            scopes=payload.scopes,
            expires_at=payload.expires_at,
            created_by_id=tenant.user_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return _api_key_response(key, raw_key)


@router.get("/api-keys", response_model=list[PublicApiKeyResponse])
def list_api_keys(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> list[PublicApiKeyResponse]:
    rows = (
        db.query(PublicApiKey)
        .filter(PublicApiKey.tenant_id == tenant.id)
        .order_by(PublicApiKey.created_at.desc())
        .all()
    )
    return [_api_key_response(item) for item in rows]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
) -> None:
    key = (
        db.query(PublicApiKey)
        .filter(PublicApiKey.tenant_id == tenant.id, PublicApiKey.id == key_id)
        .one_or_none()
    )
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    key.is_active = False
    db.commit()


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


def _job_response(job: IntegrationJob) -> IntegrationJobResponse:
    return IntegrationJobResponse(
        id=job.id,
        account_id=job.account_id,
        job_type=job.job_type,
        idempotency_key=job.idempotency_key,
        status=job.status,
        attempt=job.attempt,
        max_attempts=job.max_attempts,
        available_at=job.available_at,
        completed_at=job.completed_at,
        result=json.loads(job.result_json or "{}"),
        last_error=job.last_error,
        error_log=json.loads(job.error_log_json or "[]"),
        created_at=job.created_at,
    )


def _webhook_response(
    endpoint: WebhookEndpoint,
    signing_secret: str | None = None,
) -> WebhookEndpointResponse:
    return WebhookEndpointResponse(
        id=endpoint.id,
        title=endpoint.title,
        url=endpoint.url,
        event_types=json.loads(endpoint.event_types_json or "[]"),
        is_active=endpoint.is_active,
        signing_secret=signing_secret,
        created_at=endpoint.created_at,
    )


def _api_key_response(key: PublicApiKey, raw_key: str | None = None) -> PublicApiKeyResponse:
    return PublicApiKeyResponse(
        id=key.id,
        title=key.title,
        key_prefix=key.key_prefix,
        scopes=json.loads(key.scopes_json or "[]"),
        is_active=key.is_active,
        expires_at=key.expires_at,
        last_used_at=key.last_used_at,
        created_at=key.created_at,
        api_key=raw_key,
    )
