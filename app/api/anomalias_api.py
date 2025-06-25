from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.modelo import detectar_anomalias_por_nic, alerta_anomalia_actual
from app.services.auth import get_current_user
from app.models.user_model import User
from typing import Optional

router = APIRouter()

# ENDPOINTS SIN JWT - Solo para pruebas
@router.get("/nic/{nic}")
def obtener_anomalias(
    nic: str, 
    user_id: Optional[int] = Query(default=2, description="ID del usuario (temporal)"),
    db: Session = Depends(get_db)
):
    """
    ENDPOINT SIN JWT - Solo para pruebas
    Obtener anomalías por NIC
    
    Args:
        nic: Número de NIC a consultar
        user_id: ID del usuario (default=2)
    
    Returns:
        Lista de anomalías detectadas para el NIC
    """
    try:
        # Verificar que el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {
                "error": f"Usuario con ID {user_id} no encontrado",
                "nic": nic,
                "anomalias": []
            }
        
        return detectar_anomalias_por_nic(db, nic, user_id)
        
    except Exception as e:
        return {
            "error": f"Error obteniendo anomalías: {str(e)}",
            "nic": nic,
            "user_id": user_id
        }

@router.get("/alerta/{nic}")
def alerta_anomalia(
    nic: str, 
    user_id: Optional[int] = Query(default=2, description="ID del usuario (temporal)"),
    db: Session = Depends(get_db)
):
    """
    ENDPOINT SIN JWT - Solo para pruebas
    Obtener alerta de anomalía más reciente por NIC
    
    Args:
        nic: Número de NIC a consultar
        user_id: ID del usuario (default=2)
    
    Returns:
        Información de la anomalía más reciente
    """
    try:
        # Verificar que el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {
                "error": f"Usuario con ID {user_id} no encontrado",
                "nic": nic,
                "estado": "usuario_no_encontrado"
            }
        
        return alerta_anomalia_actual(db, nic, user_id)
        
    except Exception as e:
        return {
            "error": f"Error obteniendo alerta: {str(e)}",
            "nic": nic,
            "user_id": user_id,
            "estado": "error"
        }

# ENDPOINTS CON JWT (para producción con frontend)
@router.get("/consultar_consumo/{nic}")
def consultar_consumo(
    nic: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🎯 ENDPOINT PRINCIPAL PARA FRONTEND
    Consultar consumo y detectar anomalías usando JWT
    
    Args:
        nic: Número de NIC a consultar
    
    Returns:
        Información completa de consumo y anomalías
    """
    try:
        # Obtener alerta de anomalía más reciente
        alerta = alerta_anomalia_actual(db, nic, current_user.id)
        
        # Obtener todas las anomalías para análisis adicional
        anomalias = detectar_anomalias_por_nic(db, nic, current_user.id)
        
        # Preparar respuesta unificada
        return {
            "nic": nic,
            "usuario": current_user.email,
            "alerta_actual": alerta,
            "anomalias_historicas": anomalias,
            "resumen": {
                "tiene_anomalia_actual": alerta.get("anomalia", False) if alerta.get("estado") != "sin_datos" else False,
                "total_anomalias": len([a for a in anomalias if a.get("anomalia") == -1]) if anomalias else 0,
                "ultimo_consumo": alerta.get("consumo_kwh") if alerta.get("estado") != "sin_datos" else None,
                "fecha_ultimo": alerta.get("fecha") if alerta.get("estado") != "sin_datos" else None,
                "variacion_porcentual": alerta.get("comparado_trimestre") if alerta.get("estado") != "sin_datos" else None
            }
        }
        
    except Exception as e:
        return {
            "error": f"Error consultando consumo: {str(e)}",
            "nic": nic,
            "usuario": current_user.email,
            "alerta_actual": {"estado": "error"},
            "anomalias_historicas": [],
            "resumen": {
                "tiene_anomalia_actual": False,
                "total_anomalias": 0,
                "ultimo_consumo": None,
                "fecha_ultimo": None,
                "variacion_porcentual": None
            }
        }

@router.get("/alerta_con_jwt/{nic}")
def alerta_anomalia_con_jwt(
    nic: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener alerta de anomalía más reciente con JWT
    """
    try:
        result = alerta_anomalia_actual(db, nic, current_user.id)
        return {
            **result,
            "nic": nic,
            "usuario": current_user.email
        }
    except Exception as e:
        return {
            "error": f"Error obteniendo alerta: {str(e)}",
            "nic": nic,
            "usuario": current_user.email,
            "estado": "error"
        }

@router.get("/anomalias_con_jwt/{nic}")
def obtener_anomalias_con_jwt(
    nic: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener todas las anomalías por NIC con JWT
    """
    try:
        anomalias = detectar_anomalias_por_nic(db, nic, current_user.id)
        return {
            "nic": nic,
            "usuario": current_user.email,
            "anomalias": anomalias,
            "total_anomalias": len([a for a in anomalias if a.get("anomalia") == -1]) if anomalias else 0
        }
    except Exception as e:
        return {
            "error": f"Error obteniendo anomalías: {str(e)}",
            "nic": nic,
            "usuario": current_user.email,
            "anomalias": []
        }
