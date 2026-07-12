from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentTenant, get_current_tenant
from app.modules.analytics.schemas import AnalyticsOverview
from app.modules.analytics.service import AnalyticsService


router = APIRouter()


@router.get("/overview", response_model=AnalyticsOverview)
def analytics_overview(
    forecast_days: int = Query(default=90, ge=1, le=365),
    stuck_days: int = Query(default=14, ge=1, le=180),
    activity_days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> AnalyticsOverview:
    return AnalyticsService(db).overview(
        tenant_id=tenant.id,
        forecast_days=forecast_days,
        stuck_days=stuck_days,
        activity_days=activity_days,
    )
