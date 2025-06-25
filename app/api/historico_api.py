from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.historico_model import HistoricoConsumo
from app.models.factura_model import Factura
from app.services.auth import get_current_user
from app.models.user_model import User
from typing import Optional

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

# ENDPOINT TEMPORAL SIN JWT - HISTÓRICO POR NIC
@router.get("/nic/{nic}")
def listar_por_nic_sin_jwt(
    nic: str,
    user_id: Optional[int] = Query(default=2, description="ID del usuario (temporal)"),
    db: Session = Depends(get_db)
):
    """
    ENDPOINT TEMPORAL SIN JWT - Solo para pruebas
    Obtener histórico de consumo por NIC
    
    Args:
        nic: Número de NIC a consultar
        user_id: ID del usuario (default=2)
    
    Returns:
        Array con histórico de consumo del NIC
    """
    try:
        # Verificar que el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {
                "error": f"Usuario con ID {user_id} no encontrado",
                "nic": nic,
                "historico": []
            }
        
        # Buscar históricos por NIC y usuario
        historico = db.query(HistoricoConsumo)\
                     .join(Factura, HistoricoConsumo.factura_id == Factura.id)\
                     .filter(Factura.nic == nic, Factura.user_id == user_id)\
                     .order_by(HistoricoConsumo.fecha)\
                     .all()
        
        # Formatear respuesta
        historico_formateado = []
        for registro in historico:
            historico_formateado.append({
                "id": registro.id,
                "fecha": registro.fecha,
                "consumo_kwh": registro.consumo_kwh,
                "factura_id": registro.factura_id
            })
        
        return {
            "nic": nic,
            "total_registros": len(historico_formateado),
            "historico": historico_formateado,
            "usuario": {
                "id": user.id,
                "email": user.email
            },
            "modo": "SIN_JWT_TEMPORAL"
        }
        
    except Exception as e:
        return {
            "error": f"Error obteniendo histórico: {str(e)}",
            "nic": nic,
            "historico": [],
            "user_id": user_id
        }

# ENDPOINT ORIGINAL CON JWT (para producción)
@router.get("/nic_con_jwt/{nic}")
def listar_por_nic_con_jwt(
    nic: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint original con JWT para producción
    """
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