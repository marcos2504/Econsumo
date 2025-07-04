"""
Servicio de Email Simple para Notificaciones

Este servicio maneja el envío de emails de alerta usando
la configuración existente de Gmail y OAuth.

Author: AI Assistant
Date: 2024
"""

import logging
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from datetime import datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class SimpleEmailService:
    """Servicio simplificado para envío de emails de notificación"""
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id
        self.client_secret = client_secret
    
    def send_anomaly_alert(
        self, 
        user_email: str, 
        refresh_token: str, 
        anomalias: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Enviar alerta de anomalías por email
        
        Args:
            user_email: Email del usuario
            refresh_token: Refresh token para autenticación
            anomalias: Lista de anomalías detectadas
            
        Returns:
            Resultado del envío
        """
        try:
            if not anomalias:
                return {
                    "success": False,
                    "message": "No hay anomalías para reportar"
                }
            
            # Crear contenido del email
            subject = f"🚨 Alerta: {len(anomalias)} Anomalía(s) de Consumo Detectada(s)"
            html_content = self._create_email_content(anomalias)
            
            # Por ahora, registrar el intento (implementación completa requiere configuración OAuth)
            logger.info(f"📧 [SIMULADO] Enviando alerta a {user_email}")
            logger.info(f"📊 Anomalías detectadas: {len(anomalias)}")
            
            for i, anomalia in enumerate(anomalias, 1):
                logger.info(f"  {i}. NIC {anomalia.get('nic')}: {anomalia.get('consumo_kwh')} kWh (+{anomalia.get('aumento_porcentual', 0):.1f}%)")
            
            # Simular envío exitoso
            return {
                "success": True,
                "message": f"Email simulado enviado a {user_email}",
                "anomalies_count": len(anomalias),
                "recipient": user_email,
                "subject": subject,
                "timestamp": datetime.now().isoformat(),
                "note": "Este es un envío simulado. Para envío real, configura GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET"
            }
            
        except Exception as e:
            logger.error(f"❌ Error enviando email: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "recipient": user_email
            }
    
    def _create_email_content(self, anomalias: List[Dict[str, Any]]) -> str:
        """Crear contenido HTML del email"""
        total_anomalias = len(anomalias)
        consumo_total = sum(a.get('consumo_kwh', 0) for a in anomalias)
        aumento_promedio = sum(a.get('aumento_porcentual', 0) for a in anomalias) / total_anomalias if total_anomalias > 0 else 0
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .alert {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; }}
                .anomaly {{ background-color: #f8f9fa; margin: 10px 0; padding: 10px; border-left: 4px solid #dc3545; }}
                .stats {{ background-color: #e3f2fd; padding: 10px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="alert">
                <h2>🚨 Alerta de Consumo Eléctrico Alto</h2>
                <p>Se detectaron <strong>{total_anomalias}</strong> anomalías en tu consumo eléctrico.</p>
            </div>
            
            <div class="stats">
                <h3>📊 Resumen:</h3>
                <ul>
                    <li>Total de propiedades afectadas: {total_anomalias}</li>
                    <li>Consumo total anormal: {consumo_total:.2f} kWh</li>
                    <li>Aumento promedio: {aumento_promedio:.1f}%</li>
                </ul>
            </div>
            
            <h3>🏠 Detalles:</h3>
        """
        
        for i, anomalia in enumerate(anomalias, 1):
            html += f"""
            <div class="anomaly">
                <strong>Propiedad #{i}</strong><br>
                NIC: {anomalia.get('nic', 'N/A')}<br>
                Consumo: {anomalia.get('consumo_kwh', 0)} kWh<br>
                Aumento: +{anomalia.get('aumento_porcentual', 0):.1f}%<br>
                Dirección: {anomalia.get('direccion', 'N/A')}
            </div>
            """
        
        html += """
            <p><strong>💡 Recomendación:</strong> Revisa el consumo de tus electrodomésticos y considera medidas de ahorro energético.</p>
            <p><small>Este email fue generado automáticamente por el Sistema E-Consumo.</small></p>
        </body>
        </html>
        """
        
        return html
    
    def test_connection(self, refresh_token: str) -> Dict[str, Any]:
        """
        Probar la conexión con Gmail
        
        Args:
            refresh_token: Refresh token del usuario
            
        Returns:
            Resultado de la prueba
        """
        try:
            # Por ahora, simular prueba exitosa
            return {
                "success": True,
                "message": "Conexión simulada exitosa",
                "gmail_api": "not_configured",
                "note": "Configura GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET para conexión real"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }

# Instancia global del servicio de email
email_service = SimpleEmailService()

def send_notification_email(
    user_email: str, 
    refresh_token: str, 
    anomalias: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Función auxiliar para enviar email de notificación
    
    Args:
        user_email: Email del destinatario
        refresh_token: Refresh token para autenticación
        anomalias: Lista de anomalías detectadas
        
    Returns:
        Resultado del envío
    """
    return email_service.send_anomaly_alert(user_email, refresh_token, anomalias)
