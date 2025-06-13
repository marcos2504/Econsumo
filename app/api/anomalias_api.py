from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.modelo import detectar_anomalias_por_nic, alerta_anomalia_actual
from app.services.auth import get_current_user
from app.models.user_model import User

router = APIRouter()

@router.get("/nic/{nic}")
def obtener_anomalias(
    nic: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return detectar_anomalias_por_nic(db, nic, current_user.id)

@router.get("/alerta/{nic}")
def alerta_anomalia(
    nic: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return alerta_anomalia_actual(db, nic, current_user.id)
