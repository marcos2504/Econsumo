import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.db.session import SessionLocal
from app.models.user_model import User
from app.models.factura_model import Factura
from app.crud.user_crud import get_user_by_email
from app.services.extractor import get_service, get_edemsa_links, descargar_factura_pdf
from app.services.modelo import detectar_anomalias_por_nic, alerta_anomalia_actual
from app.services.auth import SCOPES
from app.config.notifications_config import GOOGLE_OAUTH_CONFIG, GMAIL_CONFIG, ANOMALY_CONFIG

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificacionService:
    """Servicio para gestionar notificaciones automáticas de anomalías de consumo"""
    
    def __init__(self):
        self.smtp_server = GMAIL_CONFIG["smtp_server"]
        self.smtp_port = GMAIL_CONFIG["smtp_port"]
    
    def obtener_usuarios_con_refresh_token(self, db: Session) -> List[User]:
        """Obtener todos los usuarios que tienen refresh token configurado"""
        return db.query(User).filter(
            User.gmail_refresh_token.isnot(None),
            User.gmail_refresh_token != "",
            User.is_active == True
        ).all()
    
    def obtener_ultima_fecha_lectura(self, db: Session, user_id: int) -> datetime:
        """Obtener la fecha de la última factura procesada para un usuario"""
        # Buscar la factura más reciente por fecha_lectura
        ultima_factura = db.query(Factura).filter(
            Factura.user_id == user_id,
            Factura.fecha_lectura.isnot(None)
        ).order_by(desc(Factura.fecha_lectura)).first()
        
        if ultima_factura and ultima_factura.fecha_lectura:
            try:
                # Si fecha_lectura es string, parsearlo
                if isinstance(ultima_factura.fecha_lectura, str):
                    # Intentar varios formatos de fecha
                    formatos = ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S']
                    for formato in formatos:
                        try:
                            fecha_parsed = datetime.strptime(ultima_factura.fecha_lectura, formato)
                            logger.info(f"📅 Última fecha de lectura para usuario {user_id}: {fecha_parsed}")
                            return fecha_parsed
                        except ValueError:
                            continue
                    # Si no se puede parsear, usar la fecha como referencia pero buscar desde hace 7 días
                    logger.warning(f"No se pudo parsear fecha_lectura: {ultima_factura.fecha_lectura}")
                    return datetime.now() - timedelta(days=7)
                elif isinstance(ultima_factura.fecha_lectura, datetime):
                    logger.info(f"📅 Última fecha de lectura para usuario {user_id}: {ultima_factura.fecha_lectura}")
                    return ultima_factura.fecha_lectura
                else:
                    # Si es otro tipo, usar hace 7 días
                    logger.warning(f"Tipo de fecha_lectura no esperado: {type(ultima_factura.fecha_lectura)}")
                    return datetime.now() - timedelta(days=7)
            except Exception as e:
                logger.error(f"Error parseando fecha_lectura: {e}")
                return datetime.now() - timedelta(days=7)
        else:
            # Si no hay facturas, buscar desde hace 30 días
            logger.info(f"📅 No hay facturas previas para usuario {user_id}, buscando desde hace 30 días")
            return datetime.now() - timedelta(days=30)
    
    def renovar_access_token(self, refresh_token: str) -> str:
        """Renovar access token usando refresh token"""
        try:
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri=GOOGLE_OAUTH_CONFIG["token_uri"],
                client_id=GOOGLE_OAUTH_CONFIG["client_id"],
                client_secret=GOOGLE_OAUTH_CONFIG["client_secret"],
                scopes=SCOPES
            )
            creds.refresh(Request())
            return creds.token
        except Exception as e:
            logger.error(f"Error renovando access token: {str(e)}")
            return None
    
    def buscar_nuevos_emails(self, user: User, desde_fecha: datetime, db: Session) -> List[str]:
        """Buscar nuevos emails de facturas desde una fecha específica"""
        try:
            logger.info(f"🔍 Buscando emails para {user.email} desde {desde_fecha.strftime('%Y-%m-%d %H:%M')}")
            
            # Renovar access token si es necesario
            if not user.gmail_token:
                logger.info(f"Renovando access token para {user.email}")
                nuevo_token = self.renovar_access_token(user.gmail_refresh_token)
                if not nuevo_token:
                    logger.error(f"No se pudo renovar token para usuario {user.email}")
                    return []
                
                # Actualizar token en la base de datos
                user.gmail_token = nuevo_token
                db.commit()
                db.refresh(user)
                logger.info(f"Token renovado y guardado para {user.email}")
            
            service = get_service(user.gmail_token)
            
            # Construir query con fecha más específica
            # Usar formato correcto para Gmail API (yyyy/mm/dd)
            fecha_str = desde_fecha.strftime("%Y/%m/%d")
            query = f'from:noreply@edemsa.com.ar subject:"Aviso de Factura" after:{fecha_str}'
            
            logger.info(f"Query Gmail: {query}")
            
            # Buscar mensajes
            results = service.users().messages().list(userId='me', q=query).execute()
            messages = results.get('messages', [])
            
            logger.info(f"📧 Encontrados {len(messages)} emails desde {fecha_str} para {user.email}")
            
            # Extraer links de EDEMSA
            links = []
            for msg in messages:
                try:
                    msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                    # Aquí reutilizamos la lógica del extractor existente
                    html_data = self._get_html_part(msg_data['payload'])
                    if html_data:
                        import base64
                        import re
                        html = base64.urlsafe_b64decode(html_data + '===').decode('utf-8', errors='ignore')
                        encontrados = re.findall(r'https://oficinavirtual\.edemsa\.com/facturad\.php\?conf=[^"]+', html)
                        links.extend(encontrados)
                except Exception as e:
                    logger.error(f"Error procesando email: {str(e)}")
                    continue
            
            return list(set(links))
            
        except Exception as e:
            logger.error(f"Error buscando emails para {user.email}: {str(e)}")
            return []
    
    def _get_html_part(self, payload):
        """Extraer parte HTML del payload del email"""
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/html':
                    return part['body'].get('data')
                elif part.get('parts'):
                    return self._get_html_part(part)
        elif payload.get('mimeType') == 'text/html':
            return payload['body'].get('data')
        return None
    
    def procesar_nuevas_facturas(self, user_id: int, links: List[str], db: Session) -> List[Factura]:
        """Procesar y guardar nuevas facturas con validación de duplicados"""
        import asyncio
        import concurrent.futures
        
        nuevas_facturas = []
        facturas_duplicadas = 0
        
        logger.info(f"📋 Procesando {len(links)} facturas para usuario {user_id}")
        
        # Función wrapper para ejecutar de forma síncrona
        def procesar_factura_sync(link, index):
            try:
                return descargar_factura_pdf(link, index, user_id)
            except Exception as e:
                logger.error(f"Error procesando factura {link}: {str(e)}")
                return None
        
        # Ejecutar en un thread pool para evitar conflictos con asyncio
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                for i, link in enumerate(links):
                    try:
                        logger.info(f"📄 Procesando factura {i+1}/{len(links)}")
                        # Ejecutar en un thread separado
                        future = executor.submit(procesar_factura_sync, link, i)
                        factura = future.result(timeout=300)  # 5 minutos timeout
                        
                        if factura:
                            # Verificar si ya existe esta factura
                            factura_existente = db.query(Factura).filter(
                                Factura.nic == factura.nic,
                                Factura.user_id == user_id,
                                Factura.fecha_lectura == factura.fecha_lectura
                            ).first()
                            
                            if factura_existente:
                                logger.info(f"⚠️ Factura duplicada omitida: NIC {factura.nic}, fecha {factura.fecha_lectura}")
                                facturas_duplicadas += 1
                            else:
                                nuevas_facturas.append(factura)
                                logger.info(f"✅ Procesada factura nueva: NIC {factura.nic} para usuario {user_id}")
                        
                    except concurrent.futures.TimeoutError:
                        logger.error(f"❌ Timeout procesando factura {link}")
                        continue
                    except Exception as e:
                        logger.error(f"❌ Error procesando factura {link}: {str(e)}")
                        continue
        
        except Exception as e:
            logger.error(f"❌ Error general procesando facturas: {str(e)}")
        
        logger.info(f"📊 Resultado procesamiento: {len(nuevas_facturas)} nuevas, {facturas_duplicadas} duplicadas")
        return nuevas_facturas
    
    def detectar_anomalias_nuevas(self, facturas: List[Factura], db: Session) -> List[Dict[str, Any]]:
        """Detectar anomalías en las nuevas facturas"""
        anomalias_detectadas = []
        
        logger.info(f"🔍 Analizando {len(facturas)} facturas para detectar anomalías")
        
        for factura in facturas:
            try:
                logger.info(f"Analizando factura NIC {factura.nic} - Consumo: {factura.consumo_kwh} kWh")
                
                # Usar el modelo existente para detectar anomalías
                alerta = alerta_anomalia_actual(db, factura.nic, factura.user_id)
                
                logger.info(f"Resultado análisis NIC {factura.nic}: {alerta}")
                
                if alerta.get("anomalia") == True:
                    # Verificar que supere el umbral de porcentaje configurado
                    porcentaje = alerta.get("comparado_trimestre", 0)
                    if abs(porcentaje) >= ANOMALY_CONFIG["min_increase_percentage"]:
                        anomalias_detectadas.append({
                            "factura": factura,
                            "alerta": alerta,
                            "tipo": "consumo_alto",
                            "porcentaje_aumento": porcentaje
                        })
                        logger.info(f"🚨 Anomalía detectada en NIC {factura.nic}: +{porcentaje}% respecto al trimestre")
                    else:
                        logger.info(f"⚪ Anomalía menor en NIC {factura.nic}: +{porcentaje}% (debajo del umbral {ANOMALY_CONFIG['min_increase_percentage']}%)")
                else:
                    logger.info(f"✅ Consumo normal en NIC {factura.nic}")
                
            except Exception as e:
                logger.error(f"❌ Error detectando anomalías para NIC {factura.nic}: {str(e)}")
                continue
        
        logger.info(f"📊 Anomalías detectadas: {len(anomalias_detectadas)} de {len(facturas)} facturas")
        return anomalias_detectadas
    
    def enviar_alerta_email(self, user: User, anomalias: List[Dict[str, Any]]) -> bool:
        """Enviar email de alerta al usuario"""
        try:
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = user.email  # Usar el email del usuario como remitente
            msg['To'] = user.email
            msg['Subject'] = "⚠️ Alerta de Consumo Eléctrico Alto - E-Consumo App"
            
            # Crear contenido HTML
            html_content = self._crear_contenido_html_alerta(user, anomalias)
            msg.attach(MIMEText(html_content, 'html'))
            
            # Enviar usando SMTP con las credenciales del usuario
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            
            # Aquí necesitarías implementar autenticación SMTP
            # Por ahora, usar el access token para autenticar
            # (En una implementación real, necesitarías configurar app passwords)
            
            # Por simplicidad, vamos a usar un enfoque diferente:
            # Enviar a través de la API de Gmail
            return self._enviar_via_gmail_api(user, html_content)
            
        except Exception as e:
            logger.error(f"Error enviando email a {user.email}: {str(e)}")
            return False
    
    def _enviar_via_gmail_api(self, user: User, contenido_html: str) -> bool:
        """Enviar email usando Gmail API"""
        try:
            service = get_service(user.gmail_token)
            
            # Crear mensaje
            message = MIMEMultipart()
            message['To'] = user.email
            message['Subject'] = "⚠️ Alerta de Consumo Eléctrico Alto - E-Consumo App"
            message.attach(MIMEText(contenido_html, 'html'))
            
            import base64
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Enviar mensaje
            service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"Email de alerta enviado exitosamente a {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email via Gmail API a {user.email}: {str(e)}")
            return False
    
    def _crear_contenido_html_alerta(self, user: User, anomalias: List[Dict[str, Any]]) -> str:
        """Crear contenido HTML para el email de alerta"""
        nombre = user.full_name or user.email.split('@')[0]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background-color: #ff6b35; color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center; }}
                .content {{ padding: 20px 0; }}
                .anomalia {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 10px 10px; }}
                .btn {{ background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ Alerta de Consumo Eléctrico</h1>
                    <p>E-Consumo App</p>
                </div>
                
                <div class="content">
                    <h2>Hola {nombre},</h2>
                    <p>Hemos detectado anomalías en tu consumo eléctrico que requieren tu atención:</p>
                    
        """
        
        for anomalia in anomalias:
            factura = anomalia["factura"]
            alerta = anomalia["alerta"]
            porcentaje = anomalia.get("porcentaje_aumento", 0)
            
            html += f"""
                    <div class="anomalia">
                        <h3>🏠 Propiedad: {factura.nic}</h3>
                        <p><strong>Dirección:</strong> {factura.direccion}</p>
                        <p><strong>Fecha de lectura:</strong> {factura.fecha_lectura}</p>
                        <p><strong>Consumo actual:</strong> {factura.consumo_kwh} kWh</p>
                        <p><strong>Variación respecto al trimestre:</strong> 
                           <span style="color: {'red' if porcentaje > 0 else 'green'};">
                               {'+' if porcentaje > 0 else ''}{porcentaje}%
                           </span>
                        </p>
                        <p><strong>Score de anomalía:</strong> {alerta.get('score', 'N/A')}</p>
                    </div>
            """
        
        html += f"""
                    <p>Te recomendamos revisar tu consumo en la app y verificar si hay algún equipo funcionando de manera inusual.</p>
                    
                    <a href="#" class="btn">Abrir E-Consumo App</a>
                    
                    <h3>💡 Consejos para reducir el consumo:</h3>
                    <ul>
                        <li>Verifica que no haya equipos encendidos innecesariamente</li>
                        <li>Revisa el funcionamiento de aires acondicionados y calefactores</li>
                        <li>Controla el estado de electrodomésticos antiguos</li>
                        <li>Considera el uso de temporizadores para equipos de alto consumo</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p>Este es un mensaje automático de E-Consumo App.</p>
                    <p>Fecha de envío: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                    <p>Si no deseas recibir estas notificaciones, puedes desactivarlas en la configuración de la app.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def procesar_notificaciones_usuario(self, user: User, db: Session) -> Dict[str, Any]:
        """Procesar notificaciones para un usuario específico"""
        resultado = {
            "user_id": user.id,
            "email": user.email,
            "emails_nuevos": 0,
            "facturas_procesadas": 0,
            "facturas_duplicadas": 0,
            "anomalias_detectadas": 0,
            "email_enviado": False,
            "errores": [],
            "ultima_fecha_procesamiento": None
        }
        
        try:
            # 1. Obtener última fecha de procesamiento
            ultima_fecha = self.obtener_ultima_fecha_lectura(db, user.id)
            resultado["ultima_fecha_procesamiento"] = ultima_fecha.isoformat()
            logger.info(f"👤 Procesando usuario {user.email} desde {ultima_fecha.strftime('%Y-%m-%d %H:%M')}")
            
            # 2. Buscar nuevos emails
            links = self.buscar_nuevos_emails(user, ultima_fecha, db)
            resultado["emails_nuevos"] = len(links)
            
            if not links:
                logger.info(f"📭 No hay emails nuevos para {user.email}")
                return resultado
            
            # 3. Procesar nuevas facturas
            nuevas_facturas = self.procesar_nuevas_facturas(user.id, links, db)
            resultado["facturas_procesadas"] = len(nuevas_facturas)
            
            # Calcular duplicadas (total links - facturas procesadas)
            resultado["facturas_duplicadas"] = len(links) - len(nuevas_facturas)
            
            if not nuevas_facturas:
                logger.info(f"📄 No se procesaron facturas nuevas para {user.email} (todas duplicadas)")
                return resultado
            
            # 4. Detectar anomalías
            anomalias = self.detectar_anomalias_nuevas(nuevas_facturas, db)
            resultado["anomalias_detectadas"] = len(anomalias)
            
            if not anomalias:
                logger.info(f"✅ No se detectaron anomalías para {user.email}")
                return resultado
            
            # 5. Enviar alerta por email
            email_enviado = self.enviar_alerta_email(user, anomalias)
            resultado["email_enviado"] = email_enviado
            
            if email_enviado:
                logger.info(f"📧 Alerta enviada exitosamente a {user.email}")
            else:
                resultado["errores"].append("Error enviando email de alerta")
            
        except Exception as e:
            error_msg = f"Error procesando usuario {user.email}: {str(e)}"
            logger.error(error_msg)
            resultado["errores"].append(error_msg)
        
        return resultado
    
    def ejecutar_servicio_notificaciones(self) -> Dict[str, Any]:
        """Ejecutar el servicio completo de notificaciones para todos los usuarios"""
        logger.info("🚀 Iniciando servicio de notificaciones automáticas")
        
        resultado = {
            "timestamp": datetime.now().isoformat(),
            "usuarios_procesados": 0,
            "total_emails_nuevos": 0,
            "total_facturas_procesadas": 0,
            "total_facturas_duplicadas": 0,
            "total_anomalias_detectadas": 0,
            "alertas_enviadas": 0,
            "usuarios_con_errores": 0,
            "detalles": []
        }
        
        db = SessionLocal()
        try:
            # Obtener usuarios con refresh token
            usuarios = self.obtener_usuarios_con_refresh_token(db)
            logger.info(f"👥 Encontrados {len(usuarios)} usuarios con refresh token")
            
            if not usuarios:
                logger.warning("⚠️ No hay usuarios con refresh token configurado")
                return resultado
            
            for user in usuarios:
                logger.info(f"🔄 Procesando usuario {user.email}...")
                user_resultado = self.procesar_notificaciones_usuario(user, db)
                resultado["detalles"].append(user_resultado)
                
                # Agregar al resumen
                resultado["usuarios_procesados"] += 1
                resultado["total_emails_nuevos"] += user_resultado["emails_nuevos"]
                resultado["total_facturas_procesadas"] += user_resultado["facturas_procesadas"]
                resultado["total_facturas_duplicadas"] += user_resultado.get("facturas_duplicadas", 0)
                resultado["total_anomalias_detectadas"] += user_resultado["anomalias_detectadas"]
                
                if user_resultado["email_enviado"]:
                    resultado["alertas_enviadas"] += 1
                
                if user_resultado["errores"]:
                    resultado["usuarios_con_errores"] += 1
                
                logger.info(f"✅ Usuario {user.email} procesado: "
                          f"{user_resultado['emails_nuevos']} emails, "
                          f"{user_resultado['facturas_procesadas']} facturas nuevas, "
                          f"{user_resultado.get('facturas_duplicadas', 0)} duplicadas, "
                          f"{user_resultado['anomalias_detectadas']} anomalías")
            
            # Resumen final
            logger.info("📊 RESUMEN FINAL:")
            logger.info(f"  • Usuarios procesados: {resultado['usuarios_procesados']}")
            logger.info(f"  • Total emails nuevos: {resultado['total_emails_nuevos']}")
            logger.info(f"  • Total facturas procesadas: {resultado['total_facturas_procesadas']}")
            logger.info(f"  • Total facturas duplicadas: {resultado['total_facturas_duplicadas']}")
            logger.info(f"  • Total anomalías detectadas: {resultado['total_anomalias_detectadas']}")
            logger.info(f"  • Alertas enviadas: {resultado['alertas_enviadas']}")
            logger.info(f"  • Usuarios con errores: {resultado['usuarios_con_errores']}")
            
            logger.info(f"✅ Servicio completado: {resultado['alertas_enviadas']} alertas enviadas de {resultado['usuarios_procesados']} usuarios")
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando servicio de notificaciones: {str(e)}")
            resultado["error_general"] = str(e)
        finally:
            db.close()
        
        return resultado

# Instancia global del servicio
notificacion_service = NotificacionService()
