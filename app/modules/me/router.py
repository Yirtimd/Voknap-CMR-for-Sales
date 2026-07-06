from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentTenant, get_current_tenant, get_current_user
from app.modules.accounts.models import User
from app.modules.me.schemas import MeResponse


router = APIRouter()


@router.get("/me", response_model=MeResponse)
def me(
    user: User = Depends(get_current_user),
    tenant: CurrentTenant = Depends(get_current_tenant),
) -> MeResponse:
    return MeResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=tenant.id,
        role=tenant.role,
    )

