from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.core.rbac import Permission, Role


class MeResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    full_name: str
    tenant_id: UUID
    role: Role
    permissions: list[Permission]
