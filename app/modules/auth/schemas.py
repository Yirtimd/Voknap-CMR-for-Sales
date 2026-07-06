from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


def validate_bcrypt_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be 72 bytes or shorter")
    return password


class RegisterCompanyRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=255)
    company_slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    owner_email: EmailStr
    owner_full_name: str = Field(min_length=2, max_length=255)
    owner_password: str = Field(min_length=8, max_length=72)

    @model_validator(mode="after")
    def validate_password(self) -> "RegisterCompanyRequest":
        validate_bcrypt_password(self.owner_password)
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

    @model_validator(mode="after")
    def validate_password(self) -> "LoginRequest":
        validate_bcrypt_password(self.password)
        return self


class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    tenants: list[TenantResponse]
