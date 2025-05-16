from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud.factura_crud import get_facturas
from app.services.extractor import sincronizar_facturas

router = APIRouter()

@router.get("/")
def listar_facturas(db: Session = Depends(get_db)):
    return get_facturas(db)

@router.post("/sync")
def sync_facturas():
    return sincronizar_facturas()

