from uuid import UUID

from pydantic import BaseModel, EmailStr


class MeResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    full_name: str
    tenant_id: UUID
    role: str

