from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud.factura_crud import get_facturas
from app.services.extractor import sincronizar_facturas
from app.services.database import init_db_if_not_exists
from app.models.factura_model import Factura
from app.services.auth import get_current_user
from app.models.user_model import User

router = APIRouter()

@router.get("/")
def listar_facturas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Filtrar facturas por usuario
    return db.query(Factura).filter(Factura.user_id == current_user.id).all()

@router.post("/sync")
def sync_facturas(
    current_user: User = Depends(get_current_user)
):
    # Inicializar base de datos si no existe
    if not init_db_if_not_exists():
        return {"error": "No se pudo inicializar la base de datos"}
    
    try:
        # Obtener el token de Gmail guardado en la base de datos
        gmail_token = current_user.gmail_token
        
        if gmail_token:
            # Usar el token de Gmail del usuario
            result = sincronizar_facturas(current_user.id, gmail_token)
            return {
                **result,
                "token_source": "database",
                "user_email": current_user.email
            }
        else:
            # Intentar con token.json como fallback
            result = sincronizar_facturas(current_user.id)
            return {
                **result,
                "token_source": "token.json",
                "user_email": current_user.email
            }
            
    except Exception as e:
        return {
            "error": f"Error durante la sincronización: {str(e)}",
            "user_id": current_user.id,
            "user_email": current_user.email,
            "has_gmail_token": bool(current_user.gmail_token),
            "mensaje": "Si no tienes token de Gmail guardado, proporciona gmail_token en /auth/google o asegúrate de tener token.json"
        }

@router.get("/nics")
def obtener_nics_unicos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Filtrar NICs por usuario
    resultados = db.query(Factura.nic).filter(Factura.user_id == current_user.id).distinct().all()
    return [r[0] for r in resultados]


