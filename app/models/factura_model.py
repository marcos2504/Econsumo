from sqlalchemy import Column, Integer, String, Float
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