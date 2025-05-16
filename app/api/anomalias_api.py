from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.modelo import detectar_anomalias_por_nic,alerta_anomalia_actual

router = APIRouter()

@router.get("/nic/{nic}")
def obtener_anomalias(nic: str, db: Session = Depends(get_db)):
    return detectar_anomalias_por_nic(db, nic)

@router.get("/alerta/{nic}")
def alerta_anomalia(nic: str, db: Session = Depends(get_db)):
    return alerta_anomalia_actual(db, nic)
