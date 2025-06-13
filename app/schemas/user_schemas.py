from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: str
    full_name: str
    picture: Optional[str] = None

class UserCreate(UserBase):
    google_id: str

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