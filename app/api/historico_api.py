from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.historico_model import HistoricoConsumo
from app.models.factura_model import Factura

router = APIRouter()

@router.get("/")
def listar_todo(db: Session = Depends(get_db)):
    return db.query(HistoricoConsumo).all()

@router.get("/nic/{nic}")
def listar_por_nic(nic: str, db: Session = Depends(get_db)):
    # Buscar históricos a través de la relación con facturas
    return db.query(HistoricoConsumo)\
             .join(Factura, HistoricoConsumo.factura_id == Factura.id)\
             .filter(Factura.nic == nic)\
             .all()

@router.get("/factura/{factura_id}")
def listar_por_factura(factura_id: int, db: Session = Depends(get_db)):
    return db.query(HistoricoConsumo).filter(HistoricoConsumo.factura_id == factura_id).all()