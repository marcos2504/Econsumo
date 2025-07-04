from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.auth import get_current_user_from_token
from app.models.user_model import User
from app.services.notificaciones import notificacion_service
from app.config.notifications_config import ANOMALY_CONFIG, GMAIL_CONFIG
from typing import Dict, Any
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/disparar_servicio_notificaciones")
async def disparar_servicio_notificaciones(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Disparar manualmente el servicio de notificaciones para todos los usuarios
    """
    try:
        logger.info(f"Usuario {current_user.email} disparó el servicio de notificaciones manualmente")
        
        # Ejecutar en background
        background_tasks.add_task(notificacion_service.ejecutar_servicio_notificaciones)
        
        return {
            "mensaje": "Servicio de notificaciones iniciado en segundo plano",
            "disparado_por": current_user.email,
            "estado": "procesando"
        }
        
    except Exception as e:
        logger.error(f"Error disparando servicio de notificaciones: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error disparando servicio: {str(e)}"
        )

@router.post("/verificar_notificaciones_usuario")
async def verificar_notificaciones_usuario(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Verificar y procesar notificaciones solo para el usuario actual
    """
    try:
        logger.info(f"Verificando notificaciones para usuario {current_user.email}")
        
        # Verificar si el usuario tiene refresh token
        if not current_user.gmail_refresh_token:
            return {
                "mensaje": "Usuario no tiene refresh token configurado",
                "usuario": current_user.email,
                "estado": "sin_configurar",
                "accion_requerida": "Debe autorizar el acceso a Gmail en la configuración"
            }
        
        # Procesar notificaciones para este usuario específico
        resultado = notificacion_service.procesar_notificaciones_usuario(current_user, db)
        
        return {
            "mensaje": "Verificación completada",
            "usuario": current_user.email,
            "estado": "completado",
            "resultado": resultado
        }
        
    except Exception as e:
        logger.error(f"Error verificando notificaciones para usuario {current_user.email}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error verificando notificaciones: {str(e)}"
        )

@router.get("/estado_servicio_notificaciones")
async def estado_servicio_notificaciones(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Obtener el estado del servicio de notificaciones
    """
    try:
        # Obtener usuarios con refresh token
        usuarios_configurados = notificacion_service.obtener_usuarios_con_refresh_token(db)
        
        # Verificar configuración del usuario actual
        usuario_actual_configurado = current_user.gmail_refresh_token is not None
        
        # Obtener estadísticas
        from app.models.factura_model import Factura
        from datetime import datetime, timedelta
        
        # Facturas procesadas en las últimas 24 horas
        hace_24h = datetime.now() - timedelta(hours=24)
        facturas_recientes = db.query(Factura).filter(
            Factura.created_at >= hace_24h
        ).count()
        
        return {
            "servicio_activo": True,
            "usuarios_total_configurados": len(usuarios_configurados),
            "usuario_actual_configurado": usuario_actual_configurado,
            "facturas_procesadas_24h": facturas_recientes,
            "configuracion": {
                "intervalo_monitoreo": "2 horas (configurado)",
                "umbral_anomalia": f"{ANOMALY_CONFIG['min_increase_percentage']}%",
                "emails_max_por_verificacion": GMAIL_CONFIG["max_emails_per_check"]
            },
            "usuarios_configurados": [
                {
                    "email": usuario.email,
                    "tiene_refresh_token": bool(usuario.gmail_refresh_token),
                    "ultima_actividad": usuario.updated_at.isoformat() if usuario.updated_at else None
                }
                for usuario in usuarios_configurados
            ]
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estado del servicio: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estado: {str(e)}"
        )

@router.post("/test_envio_alerta")
async def test_envio_alerta(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Enviar una alerta de prueba al usuario actual
    """
    try:
        if not current_user.gmail_refresh_token:
            raise HTTPException(
                status_code=400,
                detail="Usuario no tiene refresh token configurado"
            )
        
        # Crear datos de prueba para la alerta
        anomalias_prueba = [{
            "factura": type('obj', (object,), {
                'nic': '12345678',
                'direccion': 'Dirección de Prueba 123',
                'fecha_lectura': '12/2024',
                'consumo_kwh': 850,
                'user_id': current_user.id
            })(),
            "alerta": {
                "fecha": "2024-12-15",
                "consumo_kwh": 850,
                "anomalia": True,
                "score": -0.8,
                "comparado_trimestre": 35.5
            },
            "tipo": "consumo_alto",
            "porcentaje_aumento": 35.5
        }]
        
        # Enviar alerta de prueba
        exito = notificacion_service.enviar_alerta_email(current_user, anomalias_prueba)
        
        return {
            "mensaje": "Test de alerta completado",
            "usuario": current_user.email,
            "email_enviado": exito,
            "estado": "exitoso" if exito else "fallido"
        }
        
    except Exception as e:
        logger.error(f"Error en test de alerta para {current_user.email}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en test de alerta: {str(e)}"
        )
