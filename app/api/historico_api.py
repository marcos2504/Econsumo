from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.historico_model import HistoricoConsumo
from app.models.factura_model import Factura
from app.services.auth import get_current_user
from app.models.user_model import User

router = APIRouter()

@router.get("/")
def listar_todo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Filtrar histórico por usuario a través de las facturas
    return db.query(HistoricoConsumo)\
             .join(Factura, HistoricoConsumo.factura_id == Factura.id)\
             .filter(Factura.user_id == current_user.id)\
             .all()

@router.get("/nic/{nic}")
def listar_por_nic(
    nic: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Buscar históricos por NIC y usuario
    return db.query(HistoricoConsumo)\
             .join(Factura, HistoricoConsumo.factura_id == Factura.id)\
             .filter(Factura.nic == nic, Factura.user_id == current_user.id)\
             .all()

@router.get("/factura/{factura_id}")
def listar_por_factura(
    factura_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar que la factura pertenece al usuario
    factura = db.query(Factura).filter(
        Factura.id == factura_id, 
        Factura.user_id == current_user.id
    ).first()
    
    if not factura:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    return db.query(HistoricoConsumo).filter(HistoricoConsumo.factura_id == factura_id).all()