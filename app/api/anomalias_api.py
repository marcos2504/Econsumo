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
                "anomalias": [],
                "total_anomalias": 0
            }
        
        # Obtener anomalías (lista directa de diccionarios)
        anomalias_raw = detectar_anomalias_por_nic(db, nic, user_id)
        
        # Procesar las anomalías si hay resultados
        anomalias_procesadas = []
        if isinstance(anomalias_raw, list):
            for anomalia in anomalias_raw:
                # Convertir anomalia de -1/1 a boolean
                es_anomalia = anomalia.get("anomalia", 1) == -1
                
                anomalias_procesadas.append({
                    "id": anomalia.get("id"),
                    "fecha": str(anomalia.get("fecha", "")),
                    "consumo_kwh": float(anomalia.get("consumo_kwh", 0)),
                    "factura_id": anomalia.get("factura_id"),
                    "trimestre": anomalia.get("trimestre"),
                    "año": anomalia.get("año"),
                    "anomalia": 1 if es_anomalia else 0,
                    "score": float(anomalia.get("score", 0)),
                    "comparado_trimestre": float(anomalia.get("comparado_trimestre", 0))
                })
        
        return {
            "nic": nic,
            "usuario": user.email,
            "anomalias": anomalias_procesadas,
            "total_anomalias": len(anomalias_procesadas)
        }
        
    except Exception as e:
        return {
            "error": f"Error obteniendo anomalías: {str(e)}",
            "nic": nic,
            "user_id": user_id,
            "anomalias": [],
            "total_anomalias": 0
        }

@router.get("/anomalias_con_jwt/{nic}")
def obtener_anomalia_con_jwt(
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
        # Obtener anomalías usando el servicio existente (devuelve lista directamente)
        anomalias_raw = detectar_anomalias_por_nic(db, nic, current_user.id)
        
        # Procesar las anomalías para el formato esperado
        anomalias_lista = []
        
        # anomalias_raw es directamente una lista de diccionarios
        if isinstance(anomalias_raw, list):
            for anomalia in anomalias_raw:
                # Convertir anomalia de -1/1 a 0/1 para el frontend
                es_anomalia = anomalia.get("anomalia", 1) == -1
                
                anomalias_lista.append({
                    "fecha": str(anomalia.get("fecha", "")),
                    "consumo_kwh": float(anomalia.get("consumo_kwh", 0)),
                    "anomalia": 1 if es_anomalia else 0,
                    "comparado_trimestre": float(anomalia.get("comparado_trimestre", 0)),
                    "mensaje": f"Consumo {'anómalo' if es_anomalia else 'normal'} para el trimestre"
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
        anomalias_raw = detectar_anomalias_por_nic(db, nic, user_id)
        anomalias_historicas = []
        
        # anomalias_raw es directamente una lista de diccionarios
        if isinstance(anomalias_raw, list):
            for anomalia in anomalias_raw:
                # Convertir anomalia de -1/1 a 0/1 para el frontend
                es_anomalia = anomalia.get("anomalia", 1) == -1
                
                anomalias_historicas.append({
                    "fecha": str(anomalia.get("fecha", "")),
                    "consumo_kwh": float(anomalia.get("consumo_kwh", 0)),
                    "anomalia": 1 if es_anomalia else 0,
                    "comparado_trimestre": float(anomalia.get("comparado_trimestre", 0)),
                    "mensaje": f"Consumo {'anómalo' if es_anomalia else 'normal'} para el trimestre"
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

@router.get("/ultimo_consumo/{nic}")
def consultar_ultimo_consumo(
    nic: str,
    user_id: Optional[int] = Query(default=2, description="ID del usuario (temporal)"),
    db: Session = Depends(get_db)
):
    """
    🎯 BOTÓN "CONSULTAR CONSUMO" - ÚLTIMO CONSUMO Y ALERTA
    Endpoint optimizado para mostrar el último consumo registrado
    y determinar si es una anomalía
    
    Args:
        nic: Número de NIC a consultar
        user_id: ID del usuario (default=2)
    
    Returns:
        Información del último consumo:
        - nic: String
        - fecha: String
        - consumo_kwh: Float
        - es_anomalia: Boolean
        - variacion_trimestre: Float
        - mensaje: String
        - estado: String
    """
    try:
        # Verificar que el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {
                "nic": nic,
                "usuario": "Usuario no encontrado",
                "estado": "error",
                "mensaje": f"Usuario con ID {user_id} no encontrado"
            }
        
        # Obtener alerta del último consumo
        alerta_info = alerta_anomalia_actual(db, nic, user_id)
        
        if not alerta_info or alerta_info.get("estado") == "sin_datos":
            return {
                "nic": nic,
                "usuario": user.email,
                "estado": "sin_datos",
                "mensaje": "No hay datos de consumo registrados para este NIC"
            }
        
        # Determinar si es anomalía
        es_anomalia = alerta_info.get("anomalia", False)
        variacion = alerta_info.get("comparado_trimestre", 0)
        
        # Crear mensaje descriptivo
        if es_anomalia:
            if variacion > 0:
                mensaje = f"⚠️ ANOMALÍA DETECTADA: Consumo {variacion:.1f}% mayor que el trimestre anterior"
            else:
                mensaje = f"⚠️ ANOMALÍA DETECTADA: Consumo {abs(variacion):.1f}% menor que el trimestre anterior"
        else:
            if variacion > 0:
                mensaje = f"✅ Consumo normal: {variacion:.1f}% mayor que el trimestre anterior"
            else:
                mensaje = f"✅ Consumo normal: {abs(variacion):.1f}% menor que el trimestre anterior"
        
        return {
            "nic": nic,
            "usuario": user.email,
            "fecha": alerta_info.get("fecha"),
            "consumo_kwh": alerta_info.get("consumo_kwh"),
            "es_anomalia": es_anomalia,
            "variacion_trimestre": variacion,
            "score_anomalia": alerta_info.get("score", 0),
            "mensaje": mensaje,
            "estado": "success"
        }
        
    except Exception as e:
        return {
            "nic": nic,
            "usuario": "Error",
            "estado": "error",
            "mensaje": f"Error consultando último consumo: {str(e)}"
        }

@router.get("/ultimo_consumo_con_jwt/{nic}")
def consultar_ultimo_consumo_con_jwt(
    nic: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔐 BOTÓN "CONSULTAR CONSUMO" CON JWT - ÚLTIMO CONSUMO Y ALERTA
    Versión con autenticación JWT del endpoint anterior
    """
    try:
        # Obtener alerta del último consumo
        alerta_info = alerta_anomalia_actual(db, nic, current_user.id)
        
        if not alerta_info or alerta_info.get("estado") == "sin_datos":
            return {
                "nic": nic,
                "usuario": current_user.email,
                "estado": "sin_datos",
                "mensaje": "No hay datos de consumo registrados para este NIC"
            }
        
        # Determinar si es anomalía
        es_anomalia = alerta_info.get("anomalia", False)
        variacion = alerta_info.get("comparado_trimestre", 0)
        
        # Crear mensaje descriptivo
        if es_anomalia:
            if variacion > 0:
                mensaje = f"⚠️ ANOMALÍA DETECTADA: Consumo {variacion:.1f}% mayor que el trimestre anterior"
            else:
                mensaje = f"⚠️ ANOMALÍA DETECTADA: Consumo {abs(variacion):.1f}% menor que el trimestre anterior"
        else:
            if variacion > 0:
                mensaje = f"✅ Consumo normal: {variacion:.1f}% mayor que el trimestre anterior"
            else:
                mensaje = f"✅ Consumo normal: {abs(variacion):.1f}% menor que el trimestre anterior"
        
        return {
            "nic": nic,
            "usuario": current_user.email,
            "fecha": alerta_info.get("fecha"),
            "consumo_kwh": alerta_info.get("consumo_kwh"),
            "es_anomalia": es_anomalia,
            "variacion_trimestre": variacion,
            "score_anomalia": alerta_info.get("score", 0),
            "mensaje": mensaje,
            "estado": "success"
        }
        
    except Exception as e:
        return {
            "nic": nic,
            "usuario": current_user.email,
            "estado": "error",
            "mensaje": f"Error consultando último consumo: {str(e)}"
        }

@router.get("/todas_anomalias/{nic}")
def ver_todas_anomalias(
    nic: str,
    user_id: Optional[int] = Query(default=2, description="ID del usuario (temporal)"),
    db: Session = Depends(get_db)
):
    """
    📊 BOTÓN "VER TODAS LAS ANOMALÍAS" - HISTORIAL COMPLETO
    Endpoint optimizado para mostrar todas las anomalías históricas
    con información detallada para análisis
    
    Args:
        nic: Número de NIC a consultar
        user_id: ID del usuario (default=2)
    
    Returns:
        Lista completa de anomalías:
        - nic: String
        - usuario: String
        - anomalias: List con todas las anomalías detectadas
        - resumen: Estadísticas del historial
    """
    try:
        # Verificar que el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {
                "nic": nic,
                "usuario": "Usuario no encontrado",
                "anomalias": [],
                "resumen": {
                    "total_registros": 0,
                    "total_anomalias": 0,
                    "porcentaje_anomalias": 0,
                    "periodo_analizado": "Sin datos"
                },
                "estado": "error"
            }
        
        # Obtener todas las anomalías (el modelo ya calcula todo el historial)
        anomalias_raw = detectar_anomalias_por_nic(db, nic, user_id)
        
        # Procesar las anomalías para análisis detallado
        anomalias_procesadas = []
        anomalias_detectadas = 0
        fechas = []
        
        if isinstance(anomalias_raw, list):
            for anomalia in anomalias_raw:
                # Convertir anomalia de -1/1 a boolean
                es_anomalia = anomalia.get("anomalia", 1) == -1
                if es_anomalia:
                    anomalias_detectadas += 1
                
                variacion = anomalia.get("comparado_trimestre", 0)
                fecha_str = str(anomalia.get("fecha", ""))
                fechas.append(fecha_str)
                
                # Crear mensaje descriptivo
                if es_anomalia:
                    if variacion > 0:
                        tipo_anomalia = f"Consumo excesivo (+{variacion:.1f}%)"
                        icono = "⚠️🔺"
                    else:
                        tipo_anomalia = f"Consumo muy bajo ({variacion:.1f}%)"
                        icono = "⚠️🔻"
                else:
                    tipo_anomalia = f"Consumo normal ({variacion:+.1f}%)"
                    icono = "✅"
                
                anomalias_procesadas.append({
                    "id": anomalia.get("id"),
                    "fecha": fecha_str,
                    "consumo_kwh": float(anomalia.get("consumo_kwh", 0)),
                    "es_anomalia": es_anomalia,
                    "variacion_trimestre": float(variacion),
                    "score_anomalia": float(anomalia.get("score", 0)),
                    "trimestre": anomalia.get("trimestre"),
                    "año": anomalia.get("año"),
                    "tipo_anomalia": tipo_anomalia,
                    "icono": icono,
                    "factura_id": anomalia.get("factura_id")
                })
        
        # Crear resumen estadístico
        total_registros = len(anomalias_procesadas)
        porcentaje_anomalias = (anomalias_detectadas / total_registros * 100) if total_registros > 0 else 0
        
        # Determinar periodo analizado
        if fechas:
            fechas_ordenadas = sorted(fechas)
            periodo_analizado = f"Desde {fechas_ordenadas[0]} hasta {fechas_ordenadas[-1]}"
        else:
            periodo_analizado = "Sin datos"
        
        resumen = {
            "total_registros": total_registros,
            "total_anomalias": anomalias_detectadas,
            "consumos_normales": total_registros - anomalias_detectadas,
            "porcentaje_anomalias": round(porcentaje_anomalias, 1),
            "periodo_analizado": periodo_analizado
        }
        
        return {
            "nic": nic,
            "usuario": user.email,
            "anomalias": anomalias_procesadas,
            "resumen": resumen,
            "estado": "success"
        }
        
    except Exception as e:
        return {
            "nic": nic,
            "usuario": "Error",
            "anomalias": [],
            "resumen": {
                "total_registros": 0,
                "total_anomalias": 0,
                "porcentaje_anomalias": 0,
                "periodo_analizado": "Error"
            },
            "estado": "error",
            "mensaje": f"Error obteniendo historial: {str(e)}"
        }

@router.get("/todas_anomalias_con_jwt/{nic}")
def ver_todas_anomalias_con_jwt(
    nic: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔐 BOTÓN "VER TODAS LAS ANOMALÍAS" CON JWT - HISTORIAL COMPLETO
    Versión con autenticación JWT del endpoint anterior
    """
    try:
        # Obtener todas las anomalías
        anomalias_raw = detectar_anomalias_por_nic(db, nic, current_user.id)
        
        # Procesar las anomalías para análisis detallado
        anomalias_procesadas = []
        anomalias_detectadas = 0
        fechas = []
        
        if isinstance(anomalias_raw, list):
            for anomalia in anomalias_raw:
                # Convertir anomalia de -1/1 a boolean
                es_anomalia = anomalia.get("anomalia", 1) == -1
                if es_anomalia:
                    anomalias_detectadas += 1
                
                variacion = anomalia.get("comparado_trimestre", 0)
                fecha_str = str(anomalia.get("fecha", ""))
                fechas.append(fecha_str)
                
                # Crear mensaje descriptivo
                if es_anomalia:
                    if variacion > 0:
                        tipo_anomalia = f"Consumo excesivo (+{variacion:.1f}%)"
                        icono = "⚠️🔺"
                    else:
                        tipo_anomalia = f"Consumo muy bajo ({variacion:.1f}%)"
                        icono = "⚠️🔻"
                else:
                    tipo_anomalia = f"Consumo normal ({variacion:+.1f}%)"
                    icono = "✅"
                
                anomalias_procesadas.append({
                    "fecha": fecha_str,
                    "consumo_kwh": float(anomalia.get("consumo_kwh", 0)),
                    "es_anomalia": es_anomalia,
                    "variacion_trimestre": float(variacion),
                    "score_anomalia": float(anomalia.get("score", 0)),
                    "tipo_anomalia": tipo_anomalia,
                    "icono": icono
                })
        
        # Crear resumen estadístico
        total_registros = len(anomalias_procesadas)
        porcentaje_anomalias = (anomalias_detectadas / total_registros * 100) if total_registros > 0 else 0
        
        # Determinar periodo analizado
        if fechas:
            fechas_ordenadas = sorted(fechas)
            periodo_analizado = f"Desde {fechas_ordenadas[0]} hasta {fechas_ordenadas[-1]}"
        else:
            periodo_analizado = "Sin datos"
        
        resumen = {
            "total_registros": total_registros,
            "total_anomalias": anomalias_detectadas,
            "consumos_normales": total_registros - anomalias_detectadas,
            "porcentaje_anomalias": round(porcentaje_anomalias, 1),
            "periodo_analizado": periodo_analizado
        }
        
        return {
            "nic": nic,
            "usuario": current_user.email,
            "anomalias": anomalias_procesadas,
            "resumen": resumen,
            "estado": "success"
        }
        
    except Exception as e:
        return {
            "nic": nic,
            "usuario": current_user.email,
            "anomalias": [],
            "resumen": {
                "total_registros": 0,
                "total_anomalias": 0,
                "porcentaje_anomalias": 0,
                "periodo_analizado": "Error"
            },
            "estado": "error",
            "mensaje": f"Error obteniendo historial: {str(e)}"
        }