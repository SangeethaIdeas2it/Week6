from pydantic import BaseModel, EmailStr
from typing import Optional

class UserShared(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]

class DocumentShared(BaseModel):
    id: int
    owner_id: int
    title: str
    content: Optional[str]

class PermissionShared(BaseModel):
    user_id: int
    document_id: int
    permission: str  # read, write, admin 