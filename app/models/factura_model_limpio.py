from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Factura(Base):
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True, index=True)
    nic = Column(String, index=True)
    direccion = Column(String)
    fecha_lectura = Column(String)
    consumo_kwh = Column(Float)
    link = Column(String)
    imagen = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relación con usuario
    user = relationship("User", back_populates="facturas")
