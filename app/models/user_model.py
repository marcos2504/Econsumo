from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    google_id = Column(String, unique=True, index=True)
    full_name = Column(String)  # Usar full_name como en la DB existente
    picture = Column(String)
    gmail_token = Column(Text)  # Access token para Gmail API
    gmail_refresh_token = Column(Text)  # Refresh token para renovar access token
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con facturas
    facturas = relationship("Factura", back_populates="user")
    
    # Propiedad para compatibilidad con 'name'
    @property
    def name(self):
        return self.full_name
    
    @name.setter
    def name(self, value):
        self.full_name = value