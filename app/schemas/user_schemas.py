from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: str
    full_name: str
    picture: Optional[str] = None

class UserCreate(UserBase):
    google_id: str
    gmail_token: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    picture: Optional[str] = None
    gmail_token: Optional[str] = None

class UserResponse(UserBase):
    id: int
    google_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TokenData(BaseModel):
    email: Optional[str] = None
    google_id: Optional[str] = None

# Schemas para los endpoints de autenticación
class GoogleAuthRequest(BaseModel):
    email: str
    token: str

class TokenRequest(BaseModel):
    token: str

class TokenResponse(BaseModel):
    token: str