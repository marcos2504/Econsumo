from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.db.base import Base

class HistoricoConsumo(Base):
    __tablename__ = "historico_consumo"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(String)
    consumo_kwh = Column(Float)
    factura_id = Column(Integer, ForeignKey("facturas.id"))
