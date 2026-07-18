from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.core.rbac import Role


class MembershipRoleUpdate(BaseModel):
    role: Role


class MembershipCreate(BaseModel):
    email: EmailStr
    role: Role


class MembershipResponse(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    full_name: str
    role: Role
    created_at: datetime
