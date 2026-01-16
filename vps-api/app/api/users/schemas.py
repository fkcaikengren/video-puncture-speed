from pydantic import BaseModel, ConfigDict, field_serializer
from pydantic import Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class UserBase(BaseModel):
    username: str
    role: str = "user"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    @field_serializer('created_at')
    def serialize_created_at(self, created_at: datetime, _info):
        return int(created_at.timestamp() * 1000)

    @field_serializer('updated_at')
    def serialize_updated_at(self, updated_at: datetime, _info):
        return int(updated_at.timestamp() * 1000)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginData(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user: UserResponse

class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int

class SetRoleRequest(BaseModel):
    role: str


class UpdatePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)
