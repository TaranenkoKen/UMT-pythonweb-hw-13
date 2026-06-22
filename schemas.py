from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional
from models import UserRole


class ContactBase(BaseModel):
    """Base schema for contact data."""

    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    birthday: date
    additional_data: Optional[str] = None


class ContactResponse(ContactBase):
    """Schema for returning contact data in responses."""

    id: int
    owner_id: Optional[int] = None

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    """Base schema containing only the user's email."""

    email: EmailStr


class UserResponse(UserBase):
    """Schema for returning user data in responses."""

    id: int
    is_verified: bool
    avatar: str | None = None
    role: UserRole

    class Config:
        from_attributes = True


class TokenModel(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str


class UserCreate(UserBase):
    """Schema for user registration."""

    password: str = Field(min_length=6, max_length=72)


class PasswordResetRequest(BaseModel):
    """Schema for requesting a password reset."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for confirming a password reset with a new password."""

    token: str
    new_password: str = Field(min_length=6, max_length=72)
