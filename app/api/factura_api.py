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

# 🔐 ENDPOINT CON JWT - OBTENER NICS DEL USUARIO AUTENTICADO
@router.get("/nics")
def obtener_nics_usuario_autenticado(
    formato: Optional[str] = Query(default="simple", description="Formato: 'simple' para array, 'completo' para objeto con info"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # 🔑 JWT automático
):
    """
    🔐 ENDPOINT CON JWT - Obtener NICs del usuario autenticado
    
    El usuario se obtiene automáticamente del token JWT.
    No necesitas pasar user_id desde el frontend.
    
    Args:
        formato: 'simple' → array de strings | 'completo' → objeto con info detallada
    
    Returns:
        - formato="simple": ["3005000", "3012578"]
        - formato="completo": objeto con info detallada de cada NIC
    
    Headers requeridos:
        Authorization: Bearer <tu_jwt_token>
    """
    try:
        # 🎯 Usar automáticamente current_user.id del JWT
        user_id = current_user.id
        
        # Obtener NICs únicos del usuario autenticado
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
                    "id": current_user.id,
                    "email": current_user.email
                },
                "modo": "CON_JWT_SEGURO"  # 🔐 Indicador de que usa JWT
            }
        
    except Exception as e:
        if formato == "simple":
            return []
        else:
            return {
                "error": f"Error obteniendo NICs: {str(e)}",
                "nics": [],
                "total_nics": 0,
                "user_id": current_user.id
            }

# 🔧 ENDPOINT ALTERNATIVO SIN JWT (solo para desarrollo/testing)
@router.get("/nics-dev")
def obtener_nics_sin_jwt_desarrollo(
    user_id: Optional[int] = Query(default=2, description="ID del usuario (solo desarrollo)"),
    formato: Optional[str] = Query(default="simple", description="Formato de respuesta"),
    db: Session = Depends(get_db)
):
    """
    🔧 ENDPOINT SIN JWT - Solo para desarrollo y testing
    
    ⚠️ ADVERTENCIA: Este endpoint NO es seguro para producción.
    Usar solo durante desarrollo local.
    
    Para producción usar: GET /facturas/nics (con JWT)
    """
    try:
        # Verificar que el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            if formato == "simple":
                return []
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
        
        nics_unicos = [r[0] for r in resultados if r[0]]
        
        if formato == "simple":
            return nics_unicos
        else:
            return {
                "nics": nics_unicos,
                "total_nics": len(nics_unicos),
                "usuario": {
                    "id": user.id,
                    "email": user.email
                },
                "modo": "SIN_JWT_DESARROLLO",
                "advertencia": "Este endpoint no es seguro para producción"
            }
        
    except Exception as e:
        if formato == "simple":
            return []
        return {
            "error": f"Error: {str(e)}",
            "nics": [],
            "total_nics": 0
        }


