from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.modelo import detectar_anomalias_por_nic, alerta_anomalia_actual
from app.models.user_model import User
from app.models.factura_model import Factura
from app.models.historico_model import HistoricoConsumo
from app.services.auth import get_current_user
from typing import Optional
from sqlalchemy import desc

router = APIRouter()

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

@router.get("/anomalias_con_jwt/{nic}")
def obtener_anomalias_con_jwt(
    nic: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔐 ENDPOINT CON JWT - OBTENER ANOMALÍAS
    Endpoint principal con autenticación JWT para obtener anomalías
    Compatible con AnomaliasJwtResponse de Android Kotlin
    
    Args:
        nic: Número de NIC a consultar
    
    Returns:
        Estructura AnomaliasJwtResponse con:
        - nic: String
        - usuario: String
        - anomalias: List<AnomaliaInfo>
        - total_anomalias: Int
        - error: String? (opcional)
    """
    try:
        # Obtener anomalías usando el servicio existente
        anomalias_result = detectar_anomalias_por_nic(db, nic, current_user.id)
        
        # Procesar las anomalías para el formato esperado
        anomalias_lista = []
        
        if isinstance(anomalias_result, dict) and "anomalias" in anomalias_result:
            for anomalia in anomalias_result["anomalias"]:
                anomalias_lista.append({
                    "fecha": anomalia.get("fecha"),
                    "consumo_kwh": anomalia.get("consumo_kwh"),
                    "anomalia": 1 if anomalia.get("anomalia", False) else 0,
                    "comparado_trimestre": anomalia.get("comparado_trimestre"),
                    "mensaje": anomalia.get("mensaje")
                })
        
        # Estructura final compatible con AnomaliasJwtResponse
        return {
            "nic": nic,
            "usuario": current_user.email,
            "anomalias": anomalias_lista,
            "total_anomalias": len(anomalias_lista)
        }
        
    except Exception as e:
        return {
            "nic": nic,
            "usuario": current_user.email if current_user else "Error",
            "anomalias": [],
            "total_anomalias": 0,
            "error": f"Error obteniendo anomalías: {str(e)}"
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

@router.get("/consultar_consumo/{nic}")
def consultar_consumo_completo(
    nic: str,
    user_id: Optional[int] = Query(default=2, description="ID del usuario (temporal)"),
    db: Session = Depends(get_db)
):
    """
    🔍 ENDPOINT PRINCIPAL - CONSULTAR CONSUMO Y ANOMALÍAS
    Endpoint principal que devuelve toda la información de consumo y anomalías
    Compatible con ConsumoResponse de Android Kotlin
    
    Args:
        nic: Número de NIC a consultar
        user_id: ID del usuario (default=2)
    
    Returns:
        Estructura ConsumoResponse con:
        - alerta_actual: AlertaInfo
        - anomalias_historicas: List<AnomaliaInfo>
        - resumen: ResumenConsumo
    """
    try:
        # Verificar que el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {
                "nic": nic,
                "usuario": "Usuario no encontrado",
                "alerta_actual": {
                    "nic": nic,
                    "estado": "usuario_no_encontrado",
                    "anomalia": False,
                    "mensaje": f"Usuario con ID {user_id} no encontrado"
                },
                "anomalias_historicas": [],
                "resumen": {
                    "tiene_anomalia_actual": False,
                    "total_anomalias": 0,
                    "ultimo_consumo": None,
                    "fecha_ultimo": None,
                    "variacion_porcentual": None
                }
            }
        
        # 1. OBTENER ALERTA ACTUAL
        alerta_info = alerta_anomalia_actual(db, nic, user_id)
        
        # 2. OBTENER ANOMALÍAS HISTÓRICAS
        anomalias_result = detectar_anomalias_por_nic(db, nic, user_id)
        anomalias_historicas = []
        
        if isinstance(anomalias_result, dict) and "anomalias" in anomalias_result:
            for anomalia in anomalias_result["anomalias"]:
                anomalias_historicas.append({
                    "fecha": anomalia.get("fecha"),
                    "consumo_kwh": anomalia.get("consumo_kwh"),
                    "anomalia": 1 if anomalia.get("anomalia", False) else 0,
                    "comparado_trimestre": anomalia.get("comparado_trimestre"),
                    "mensaje": anomalia.get("mensaje")
                })
        
        # 3. OBTENER ÚLTIMO CONSUMO PARA RESUMEN
        ultima_factura = db.query(Factura).filter(
            Factura.user_id == user_id,
            Factura.nic == nic
        ).order_by(desc(Factura.id)).first()
        
        ultimo_consumo = None
        fecha_ultimo = None
        variacion_porcentual = None
        
        if ultima_factura:
            # Buscar el último histórico de consumo
            ultimo_historico = db.query(HistoricoConsumo).filter(
                HistoricoConsumo.factura_id == ultima_factura.id
            ).order_by(desc(HistoricoConsumo.id)).first()
            
            if ultimo_historico:
                ultimo_consumo = ultimo_historico.consumo_kwh
                fecha_ultimo = ultimo_historico.fecha_lectura
                
                # Calcular variación si hay datos de comparación
                if hasattr(alerta_info, 'get') and alerta_info.get("comparado_trimestre"):
                    variacion_porcentual = alerta_info.get("comparado_trimestre")
        
        # 4. CREAR RESUMEN
        tiene_anomalia_actual = False
        if isinstance(alerta_info, dict):
            tiene_anomalia_actual = alerta_info.get("anomalia", False)
        
        resumen = {
            "tiene_anomalia_actual": tiene_anomalia_actual,
            "total_anomalias": len(anomalias_historicas),
            "ultimo_consumo": ultimo_consumo,
            "fecha_ultimo": fecha_ultimo,
            "variacion_porcentual": variacion_porcentual
        }
        
        # 5. ESTRUCTURA FINAL COMPATIBLE CON ConsumoResponse
        return {
            "nic": nic,
            "usuario": user.email,
            "alerta_actual": alerta_info if isinstance(alerta_info, dict) else {
                "nic": nic,
                "estado": "sin_datos",
                "anomalia": False,
                "mensaje": "No hay datos de alerta disponibles"
            },
            "anomalias_historicas": anomalias_historicas,
            "resumen": resumen
        }
        
    except Exception as e:
        return {
            "nic": nic,
            "usuario": "Error",
            "alerta_actual": {
                "nic": nic,
                "estado": "error",
                "anomalia": False,
                "mensaje": f"Error consultando consumo: {str(e)}"
            },
            "anomalias_historicas": [],
            "resumen": {
                "tiene_anomalia_actual": False,
                "total_anomalias": 0,
                "ultimo_consumo": None,
                "fecha_ultimo": None,
                "variacion_porcentual": None
            }
        }
