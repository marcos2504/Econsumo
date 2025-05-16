from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.historico_model import HistoricoConsumo

router = APIRouter()

@router.get("/")
def listar_todo(db: Session = Depends(get_db)):
    return db.query(HistoricoConsumo).all()

@router.get("/nic/{nic}")
def listar_por_nic(nic: str, db: Session = Depends(get_db)):
    return db.query(HistoricoConsumo).filter(HistoricoConsumo.nic == nic).all()

@router.get("/factura/{factura_id}")
def listar_por_factura(factura_id: int, db: Session = Depends(get_db)):
    return db.query(HistoricoConsumo).filter(HistoricoConsumo.factura_id == factura_id).all()