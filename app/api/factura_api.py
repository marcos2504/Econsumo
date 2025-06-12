from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud.factura_crud import get_facturas
from app.services.extractor import sincronizar_facturas
from app.models.factura_model import Factura

router = APIRouter()

@router.get("/")
def listar_facturas(db: Session = Depends(get_db)):
    return get_facturas(db)

@router.post("/sync")
def sync_facturas():
    return sincronizar_facturas()

@router.get("/nics")
def obtener_nics_unicos(db: Session = Depends(get_db)):
    resultados = db.query(Factura.nic).distinct().all()
    return [r[0] for r in resultados]


