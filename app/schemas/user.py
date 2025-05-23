from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


class UserBase(BaseModel):
    email: EmailStr
    username: str
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class User(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserInDBBase(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserInDB(UserInDBBase):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str


class TokenPayload(BaseModel):
    sub: Optional[int] = None
    exp: Optional[int] = None


class UserWithToken(BaseModel):
    user: User
    tokens: Token


class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: str

    @field_validator('email', 'username')
    @classmethod
    def validate_credentials(cls, v: Optional[str], info) -> Optional[str]:
        if not v and not info.data.get('username' if info.field_name == 'email' else 'email'):
            raise ValueError('Either email or username must be provided')
        return v 