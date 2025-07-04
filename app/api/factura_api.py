from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud.factura_crud import get_facturas
from app.services.extractor import sincronizar_facturas_con_limite
from app.services.database import init_db_if_not_exists
from app.models.factura_model import Factura
from app.services.auth import get_current_user
from app.models.user_model import User
from typing import Optional

router = APIRouter()

@router.get("/")
def listar_facturas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Filtrar facturas por usuario
    return db.query(Factura).filter(Factura.user_id == current_user.id).all()

# ENDPOINT TEMPORAL SIN JWT - SOLO PARA PRUEBAS
@router.get("/sync")
@router.post("/sync")
def sync_facturas_sin_jwt(
    max_emails: Optional[int] = Query(default=10, description="Número máximo de emails a procesar (1-50)"),
    user_id: Optional[int] = Query(default=2, description="ID del usuario (temporal)"),
    db: Session = Depends(get_db)
):
    """
    ENDPOINT TEMPORAL SIN JWT - Solo para pruebas
    Sincronizar facturas sin autenticación
    
    Args:
        max_emails: Número máximo de emails a procesar (1-50
    """
    
    # Validar límite de emails
    if max_emails < 1 or max_emails > 50:
        return {
            "error": "max_emails debe estar entre 1 y 50",
            "max_emails_recibido": max_emails,
            "tiempo_estimado": "N/A"
        }
    
    # Calcular tiempo estimado (30 segundos por email)
    tiempo_estimado_segundos = max_emails * 30
    if tiempo_estimado_segundos < 60:
        tiempo_estimado = f"{tiempo_estimado_segundos} segundos"
    else:
        minutos = tiempo_estimado_segundos // 60
        segundos_restantes = tiempo_estimado_segundos % 60
        if segundos_restantes > 0:
            tiempo_estimado = f"{minutos} minutos y {segundos_restantes} segundos"
        else:
            tiempo_estimado = f"{minutos} minutos"
    
    # Inicializar base de datos si no existe
    if not init_db_if_not_exists():
        return {"error": "No se pudo inicializar la base de datos"}
    
    try:
        # Buscar usuario en la DB
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {
                "error": f"Usuario con ID {user_id} no encontrado",
                "usuarios_disponibles": "Verifica los IDs de usuario en la DB"
            }
        
        gmail_token = user.gmail_token
        
        if gmail_token:
            # Usar el token de Gmail del usuario con límite
            result = sincronizar_facturas_con_limite(
                user_id=user_id, 
                gmail_token=gmail_token,
                max_emails=max_emails
            )
            return {
                **result,
                "configuracion": {
                    "max_emails_solicitados": max_emails,
                    "tiempo_estimado": tiempo_estimado,
                    "tiempo_por_email": "30 segundos"
                },
                "usuario": {
                    "id": user.id,
                    "email": user.email
                },
                "modo": "SIN_JWT_TEMPORAL"
            }
        else:
            return {
                "error": "El usuario no tiene token de Gmail guardado",
                "solucion": "El usuario debe autenticarse con Google primero",
                "usuario": {
                    "id": user.id,
                    "email": user.email,
                    "tiene_gmail_token": False
                },
                "configuracion_solicitada": {
                    "max_emails": max_emails,
                    "tiempo_estimado": tiempo_estimado
                }
            }
            
    except Exception as e:
        return {
            "error": f"Error durante la sincronización: {str(e)}",
            "user_id": user_id,
            "configuracion_solicitada": {
                "max_emails": max_emails,
                "tiempo_estimado": tiempo_estimado
            },
            "modo": "SIN_JWT_TEMPORAL"
        }

# ENDPOINT ORIGINAL CON JWT (para producción)
@router.post("/sync_con_jwt")
def sync_facturas_con_jwt(
    max_emails: Optional[int] = Query(default=10, description="Número máximo de emails a procesar (1-50)"),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint original con JWT para producción
    """
    """
    Sincronizar facturas con límite de emails
    
    Args:
        max_emails: Número máximo de emails a procesar (1-50)
    """
    
    # Validar límite de emails
    if max_emails < 1 or max_emails > 50:
        return {
            "error": "max_emails debe estar entre 1 y 50",
            "max_emails_recibido": max_emails,
            "tiempo_estimado": "N/A"
        }
    
    # Calcular tiempo estimado (30 segundos por email)
    tiempo_estimado_segundos = max_emails * 30
    if tiempo_estimado_segundos < 60:
        tiempo_estimado = f"{tiempo_estimado_segundos} segundos"
    else:
        minutos = tiempo_estimado_segundos // 60
        segundos_restantes = tiempo_estimado_segundos % 60
        if segundos_restantes > 0:
            tiempo_estimado = f"{minutos} minutos y {segundos_restantes} segundos"
        else:
            tiempo_estimado = f"{minutos} minutos"
    
    # Inicializar base de datos si no existe
    if not init_db_if_not_exists():
        return {"error": "No se pudo inicializar la base de datos"}
    
    try:
        # Obtener el token de Gmail guardado en la base de datos
        gmail_token = current_user.gmail_token
        
        if gmail_token:
            # Usar el token de Gmail del usuario con límite
            result = sincronizar_facturas_con_limite(
                user_id=current_user.id, 
                gmail_token=gmail_token,
                max_emails=max_emails
            )
            return {
                **result,
                "configuracion": {
                    "max_emails_solicitados": max_emails,
                    "tiempo_estimado": tiempo_estimado,
                    "tiempo_por_email": "30 segundos"
                },
                "token_source": "database",
                "user_email": current_user.email
            }
        else:
            return {
                "error": "No tienes token de Gmail guardado",
                "solucion": "Primero debes autenticarte con Google para obtener acceso a Gmail",
                "user_id": current_user.id,
                "user_email": current_user.email,
                "has_gmail_token": False,
                "configuracion_solicitada": {
                    "max_emails": max_emails,
                    "tiempo_estimado": tiempo_estimado
                }
            }
            
    except Exception as e:
        return {
            "error": f"Error durante la sincronización: {str(e)}",
            "user_id": current_user.id,
            "user_email": current_user.email,
            "has_gmail_token": bool(current_user.gmail_token),
            "configuracion_solicitada": {
                "max_emails": max_emails,
                "tiempo_estimado": tiempo_estimado
            }
        }

@router.get("/opciones")
def obtener_opciones_sync():
    """
    Obtener las opciones disponibles para sincronización
    """
    return {
        "max_emails": {
            "min": 1,
            "max": 50,
            "default": 10,
            "descripcion": "Número máximo de emails a procesar"
        },
        "tiempo_por_email": "30 segundos",
        "ejemplos_tiempo": [
            {"emails": 1, "tiempo": "30 segundos"},
            {"emails": 5, "tiempo": "2 minutos y 30 segundos"},
            {"emails": 10, "tiempo": "5 minutos"},
            {"emails": 20, "tiempo": "10 minutos"},
            {"emails": 30, "tiempo": "15 minutos"},
            {"emails": 50, "tiempo": "25 minutos"}
        ]
    }

@router.get("/stats")
def obtener_estadisticas_sync(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener estadísticas de sincronización del usuario
    """
    total_facturas = db.query(Factura).filter(Factura.user_id == current_user.id).count()
    
    return {
        "total_facturas": total_facturas,
        "usuario": current_user.email,
        "tiene_gmail_token": bool(current_user.gmail_token),
        "limite_recomendado": "10 emails (5 minutos)",
        "limite_maximo": "50 emails (25 minutos)"
    }

# ENDPOINT TEMPORAL SIN JWT - OBTENER NICS ÚNICOS (ARRAY SIMPLE)
@router.get("/nics")
def obtener_nics_sin_jwt(
    user_id: Optional[int] = Query(default=2, description="ID del usuario (temporal)"),
    formato: Optional[str] = Query(default="simple", description="Formato de respuesta: 'simple' para array, 'completo' para objeto"),
    db: Session = Depends(get_db)
):
    """
    ENDPOINT TEMPORAL SIN JWT - Solo para pruebas
    Obtener todos los NICs únicos asociados a un usuario
    
    Args:
        user_id: ID del usuario (default=2)
        formato: 'simple' devuelve array, 'completo' devuelve objeto con info
    
    Returns:
        Array de NICs únicos del usuario o objeto completo según formato
    """
    try:
        # Verificar que el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            if formato == "simple":
                return []
            else:
                return {
                    "error": f"Usuario con ID {user_id} no encontrado",
                    "nics": [],
                    "total_nics": 0
                }
        
        # Obtener NICs únicos del usuario
        resultados = db.query(Factura.nic).filter(
            Factura.user_id == user_id,
            Factura.nic.isnot(None),
            Factura.nic != ""
        ).distinct().all()
        
        # Extraer solo los valores de NIC (no tuplas)
        nics_unicos = [r[0] for r in resultados if r[0]]
        
        # FORMATO SIMPLE: Solo array de strings
        if formato == "simple":
            return nics_unicos
        
        # FORMATO COMPLETO: Objeto con información adicional
        else:
            # Información adicional sobre cada NIC
            nics_con_info = []
            for nic in nics_unicos:
                facturas_count = db.query(Factura).filter(
                    Factura.user_id == user_id,
                    Factura.nic == nic
                ).count()
                
                # Obtener la última factura para info adicional
                ultima_factura = db.query(Factura).filter(
                    Factura.user_id == user_id,
                    Factura.nic == nic
                ).order_by(Factura.id.desc()).first()
                
                nics_con_info.append({
                    "nic": nic,
                    "total_facturas": facturas_count,
                    "direccion": ultima_factura.direccion if ultima_factura else None,
                    "ultima_fecha": ultima_factura.fecha_lectura if ultima_factura else None
                })
            
            return {
                "nics": nics_unicos,
                "nics_con_info": nics_con_info,
                "total_nics": len(nics_unicos),
                "usuario": {
                    "id": user.id,
                    "email": user.email
                },
                "modo": "SIN_JWT_TEMPORAL"
            }
        
    except Exception as e:
        if formato == "simple":
            return []
        else:
            return {
                "error": f"Error obteniendo NICs: {str(e)}",
                "nics": [],
                "total_nics": 0,
                "user_id": user_id
            }

# ENDPOINT ORIGINAL CON JWT PARA NICS (para producción)
@router.get("/nics_con_jwt")
def obtener_nics_con_jwt(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🏠 OBTENER NICS CON DETALLES PARA SELECTOR
    Endpoint optimizado para el frontend Android con estructura exacta de NicsResponse
    
    Returns:
        Estructura compatible con data class NicsResponse de Kotlin:
        - nics: Lista de strings
        - nics_con_direccion: Lista de objetos NicConDireccion
        - selector_items: Lista de objetos SelectorItem
        - total_nics: Número total
        - usuario: Email del usuario
    """
    try:
        # Obtener NICs únicos del usuario
        nics_unicos = db.query(Factura.nic)\
                       .filter(
                           Factura.user_id == current_user.id,
                           Factura.nic.isnot(None),
                           Factura.nic != ""
                       )\
                       .distinct()\
                       .all()
        
        # Listas para la respuesta
        nics = []  # Lista simple de strings
        nics_con_direccion = []  # Lista de objetos con dirección
        selector_items = []  # Lista de items para el selector
        
        for (nic,) in nics_unicos:
            if nic:  # Verificar que el NIC no sea nulo
                # Agregar a lista simple
                nics.append(nic)
                
                # Contar facturas para este NIC
                total_facturas = db.query(Factura).filter(
                    Factura.user_id == current_user.id,
                    Factura.nic == nic
                ).count()
                
                # Obtener la última factura para info adicional
                ultima_factura = db.query(Factura).filter(
                    Factura.user_id == current_user.id,
                    Factura.nic == nic
                ).order_by(Factura.id.desc()).first()
                
                # Preparar datos
                direccion = ultima_factura.direccion if ultima_factura else "Dirección no disponible"
                ultima_fecha = ultima_factura.fecha_lectura if ultima_factura else "Sin fecha"
                
                # Crear dirección corta (primeras 30 caracteres + ...)
                direccion_corta = direccion[:30] + "..." if len(direccion) > 30 else direccion
                
                # Agregar a nics_con_direccion
                nics_con_direccion.append({
                    "nic": nic,
                    "direccion": direccion,
                    "direccion_corta": direccion_corta,
                    "ultima_fecha": ultima_fecha,
                    "total_facturas": total_facturas
                })
                
                # Crear labels para selector
                label = f"NIC: {nic}"
                label_completo = f"Propiedad NIC {nic} - {direccion_corta}"
                info = f"{total_facturas} facturas • Última: {ultima_fecha}"
                subtitle = f"{direccion_corta} • {total_facturas} facturas"
                
                # Agregar a selector_items
                selector_items.append({
                    "value": nic,
                    "label": label,
                    "label_completo": label_completo,
                    "info": info,
                    "subtitle": subtitle
                })
        
        # Respuesta en formato exacto de NicsResponse (Kotlin)
        return {
            "nics": nics,
            "nics_con_direccion": nics_con_direccion,
            "selector_items": selector_items,
            "total_nics": len(nics),
            "usuario": current_user.email
        }
        
    except Exception as e:
        return {
            "nics": [],
            "nics_con_direccion": [],
            "selector_items": [],
            "total_nics": 0,
            "usuario": current_user.email if current_user else None,
            "error": f"Error obteniendo NICs: {str(e)}"
        }

@router.get("/estado_sync")
def estado_sincronizacion(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 ESTADO DE SINCRONIZACIÓN DEL USUARIO
    Mostrar información sobre facturas y última sincronización
    
    Returns:
        Estado actual de sincronización, facturas procesadas, etc.
    """
    try:
        # Contar facturas del usuario
        total_facturas = db.query(Factura).filter(Factura.user_id == current_user.id).count()
        
        # Obtener última factura procesada
        ultima_factura = db.query(Factura)\
                         .filter(Factura.user_id == current_user.id)\
                         .order_by(Factura.id.desc())\
                         .first()
        
        # Obtener NICs únicos
        nics_query = db.query(Factura.nic)\
                      .filter(Factura.user_id == current_user.id)\
                      .distinct()
        nics_unicos = [row.nic for row in nics_query.all()]
        
        # Información de la última factura
        info_ultima = None
        if ultima_factura:
            # Contar registros históricos de la última factura
            from app.models.historico_model import HistoricoConsumo
            historicos_ultima = db.query(HistoricoConsumo)\
                               .filter(HistoricoConsumo.factura_id == ultima_factura.id)\
                               .count()
            
            info_ultima = {
                "id": ultima_factura.id,
                "nic": ultima_factura.nic,
                "fecha_procesamiento": ultima_factura.fecha_procesamiento.isoformat() if ultima_factura.fecha_procesamiento else None,
                "direccion": ultima_factura.direccion,
                "registros_historicos": historicos_ultima
            }
        
        return {
            "usuario": current_user.email,
            "estado": "sincronizado" if total_facturas > 0 else "sin_datos",
            "total_facturas": total_facturas,
            "nics_encontrados": len(nics_unicos),
            "nics": nics_unicos,
            "ultima_factura": info_ultima,
            "recomendacion": "Datos actualizados" if total_facturas > 0 else "Ejecute sincronización para obtener datos"
        }
        
    except Exception as e:
        return {
            "error": f"Error obteniendo estado de sincronización: {str(e)}",
            "usuario": current_user.email,
            "estado": "error"
        }

@router.post("/sync_inteligente_con_jwt")
def sync_inteligente_con_jwt(
    max_emails: Optional[int] = Query(default=10, description="Número máximo de emails a procesar"),
    forzar_sync: Optional[bool] = Query(default=False, description="Forzar sincronización completa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔄 SINCRONIZACIÓN INTELIGENTE CON JWT
    Sincronización optimizada que detecta si es primera vez o incremental
    
    Args:
        max_emails: Máximo número de emails a procesar (1-20)
        forzar_sync: Si es True, procesa todos los emails aunque ya existan facturas
    
    Returns:
        Resultado de la sincronización con detalles de procesamiento
    """
    try:
        # Validaciones
        if max_emails < 1 or max_emails > 20:
            return {
                "error": "max_emails debe estar entre 1 y 20 para sincronización inteligente",
                "max_emails_recibido": max_emails,
                "usuario": current_user.email
            }
        
        # Verificar si el usuario ya tiene facturas
        facturas_existentes = db.query(Factura).filter(Factura.user_id == current_user.id).count()
        
        es_primera_vez = facturas_existentes == 0
        
        if es_primera_vez:
            modo_sync = "primera_vez"
            limite_recomendado = min(max_emails, 10)  # Límite más conservador para primera vez
        elif forzar_sync:
            modo_sync = "forzada_completa"
            limite_recomendado = max_emails
        else:
            modo_sync = "incremental"
            limite_recomendado = min(max_emails, 5)  # Pocas facturas para incremental
        
        # Verificar que el usuario tenga gmail_token
        if not current_user.gmail_token:
            return {
                "error": "Usuario no tiene token de Gmail configurado",
                "usuario": current_user.email,
                "solucion": "Realice login nuevamente incluyendo permisos de Gmail",
                "sync_realizado": False
            }
        
        # Ejecutar sincronización
        resultado_sync = sincronizar_facturas_con_limite(
            user_id=current_user.id,
            gmail_token=current_user.gmail_token,
            max_emails=limite_recomendado
        )
        
        # Contar facturas después de la sincronización
        facturas_despues = db.query(Factura).filter(Factura.user_id == current_user.id).count()
        facturas_nuevas = facturas_despues - facturas_existentes
        
        # Información de resultado
        return {
            "sync_completado": True,
            "modo_sincronizacion": modo_sync,
            "es_primera_vez": es_primera_vez,
            "usuario": current_user.email,
            "emails_procesados": limite_recomendado,
            "facturas_antes": facturas_existentes,
            "facturas_despues": facturas_despues,
            "facturas_nuevas": facturas_nuevas,
            "resultado_extractor": resultado_sync,
            "recomendacion": "Sincronización completa" if facturas_nuevas > 0 else "No se encontraron facturas nuevas"
        }
        
    except Exception as e:
        return {
            "error": f"Error en sincronización inteligente: {str(e)}",
            "usuario": current_user.email,
            "sync_completado": False,
            "modo_sincronizacion": modo_sync if 'modo_sync' in locals() else "desconocido"
        }
    