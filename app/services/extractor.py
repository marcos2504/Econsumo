import os
import re
import base64
import csv
import requests
import fitz  # PyMuPDF
import pandas as pd
from playwright.sync_api import sync_playwright
from pdf2image import convert_from_path
from app.db.session import SessionLocal
from app.models.factura_model import Factura
from app.services.auth import SCOPES, TOKEN_PATH
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.services.grafico import extraer_grafico, analizar_con_gemini
from app.models.historico_model import HistoricoConsumo
from fastapi import HTTPException
from sqlalchemy.orm import Session

EMAIL_QUERY = 'subject:"Factura Digital"'

# === GMAIL ===
def get_service(gmail_token=None, refresh_token=None):
    """
    Obtener servicio de Gmail usando token OAuth o archivo token.json
    """
    try:
        if gmail_token:
            # Importar configuración OAuth
            from app.config.notifications_config import GOOGLE_OAUTH_CONFIG
            
            # Usar token OAuth con toda la información necesaria para renovación
            creds = Credentials(
                token=gmail_token,
                refresh_token=refresh_token,
                token_uri=GOOGLE_OAUTH_CONFIG["token_uri"],
                client_id=GOOGLE_OAUTH_CONFIG["client_id"],
                client_secret=GOOGLE_OAUTH_CONFIG["client_secret"],
                scopes=SCOPES
            )
        else:
            # Usar archivo token.json (método original)
            if not os.path.exists(TOKEN_PATH):
                raise FileNotFoundError(f"No se encontró {TOKEN_PATH} y no se proporcionó gmail_token")
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        
        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear servicio de Gmail: {str(e)}"
        )

def get_html_part(payload):
    if 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/html':
                return part['body'].get('data')
            elif part.get('parts'):
                return get_html_part(part)
    elif payload.get('mimeType') == 'text/html':
        return payload['body'].get('data')
    return None

def get_edemsa_links(service, max_emails=None):
    """
    Obtener links de EDEMSA con límite opcional de emails
    """
    results = service.users().messages().list(userId='me', q=EMAIL_QUERY).execute()
    messages = results.get('messages', [])
    
    # Aplicar límite si se especifica
    if max_emails and max_emails > 0:
        messages = messages[:max_emails]
        print(f"📧 Limitando búsqueda a {max_emails} emails más recientes")
    
    links = []
    emails_procesados = 0

    for msg in messages:
        emails_procesados += 1
        print(f"📧 Procesando email {emails_procesados}/{len(messages)}...")
        
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        html_data = get_html_part(msg_data['payload'])
        if not html_data:
            continue
        html = base64.urlsafe_b64decode(html_data + '===').decode('utf-8', errors='ignore')
        encontrados = re.findall(r'https://oficinavirtual\.edemsa\.com/facturad\.php\?conf=[^"]+', html)
        links.extend(encontrados)

    print(f"✅ Procesados {emails_procesados} emails, encontrados {len(links)} links únicos")
    return list(set(links))

# === PDF ===
def extraer_info_pdf(nombre_pdf):
    doc = fitz.open(nombre_pdf)
    texto = ""
    for page in doc:
        texto += page.get_text("text")

    lineas = texto.splitlines()
    nic = ""
    direccion = ""
    fecha_lectura = ""
    consumo_kwh = ""

    for linea in lineas:
        if re.fullmatch(r"\d{6,10}", linea.strip()):
            nic = linea.strip()
            break

    for i, linea in enumerate(lineas):
        if "Domicilio suministro" in linea:
            calle = lineas[i + 1].strip()
            localidad1 = lineas[i + 2].strip()
            localidad2 = lineas[i + 3].strip()
            direccion = f"{calle}, {localidad1}, {localidad2}"
            break

    fechas = re.findall(r'\d{2}/\d{2}/\d{4}', texto)
    if len(fechas) >= 2:
        fecha_lectura = fechas[1]

    energia_activa_index = None
    for i, linea in enumerate(lineas):
        if "Energía Activa" in linea:
            energia_activa_index = i
            break

    if energia_activa_index is not None:
        for linea in lineas[energia_activa_index+1:energia_activa_index+5]:
            if re.match(r'^\d+,\d{2}$', linea.strip()):
                consumo_kwh = linea.strip().replace(",", ".")

    if not consumo_kwh:
        for i, linea in enumerate(lineas):
            if "Cargo Variable" in linea and "kWh" in linea:
                if i+1 < len(lineas):
                    match = re.search(r'(\d+,\d+)', lineas[i+1])
                    if match:
                        consumo_kwh = match.group(1).replace(",", ".")

    return {
        "nic": nic,
        "direccion": direccion,
        "fecha_lectura": fecha_lectura,
        "consumo_kwh": consumo_kwh,
    }

# === Descarga PDF y guarda en DB ===
def descargar_factura_pdf(url, index, user_id):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        try:
            print(f"Abriendo sesión para descarga directa...")
            page.goto(url, timeout=90000, wait_until="load")
            page.wait_for_timeout(5000)

            cookies = context.cookies()
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": url,
            }
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
            headers["Cookie"] = cookie_str

            pdf_url = url.replace("facturad.php", "facturad_mail.php")
            nombre_archivo = f"factura_{index + 1}.pdf"
            response = requests.get(pdf_url, headers=headers)

            if response.status_code == 200 and response.headers['Content-Type'] == 'application/pdf':
                with open(nombre_archivo, "wb") as f:
                    f.write(response.content)

                datos = extraer_info_pdf(nombre_archivo)
                datos["link"] = url
                datos["imagen"] = ""

                # Guardar en DB con user_id
                db = SessionLocal()
                try:
                    factura = Factura(
                        nic=datos['nic'],
                        direccion=datos['direccion'],
                        fecha_lectura=datos['fecha_lectura'],
                        consumo_kwh=datos['consumo_kwh'],
                        link=datos['link'],
                        imagen="",
                        user_id=user_id
                    )
                    db.add(factura)
                    db.commit()
                    db.refresh(factura)

                    # Guardar datos de la factura ANTES de procesar gráfico
                    factura_data = {
                        "id": factura.id,
                        "nic": factura.nic,
                        "direccion": factura.direccion,
                        "fecha_lectura": factura.fecha_lectura,
                        "consumo_kwh": factura.consumo_kwh,
                        "link": factura.link,
                        "imagen": factura.imagen,
                        "user_id": factura.user_id
                    }

                    # Procesar gráfico
                    imagen_nombre = f"{factura.nic}_grafico.png"
                    if extraer_grafico(nombre_archivo, imagen_nombre):
                        df = analizar_con_gemini(imagen_nombre)
                        for _, row in df.iterrows():
                            registro = HistoricoConsumo(
                                fecha=row['fecha'],
                                consumo_kwh=row['consumo_wh'],
                                factura_id=factura.id
                            )
                            db.add(registro)
                        factura.imagen = imagen_nombre
                        factura_data["imagen"] = imagen_nombre
                        db.commit()

                    # Cerrar sesión DESPUÉS de completar todas las operaciones
                    db.close()
                    
                    # Crear objeto simple para retornar (no vinculado a sesión)
                    class FacturaSimple:
                        def __init__(self, data):
                            for key, value in data.items():
                                setattr(self, key, value)
                    
                    return FacturaSimple(factura_data)
                    
                except Exception as db_error:
                    db.rollback()
                    db.close()
                    print(f"[!] Error en base de datos: {db_error}")
                    return None
            else:
                return None

        except Exception as e:
            print(f"[!] Error durante la descarga del PDF: {e}")
            return None
        finally:
            browser.close()

# === Función principal de sincronización ===
def sincronizar_facturas(user_id, gmail_token=None):
    """
    Función principal de sincronización con soporte para token OAuth
    """
    try:
        service = get_service(gmail_token)
        links = get_edemsa_links(service)
        nuevas = []
        for i, link in enumerate(links):
            factura = descargar_factura_pdf(link, i, user_id)
            if factura:
                nuevas.append(factura)
        return {"facturas_sincronizadas": len(nuevas), "facturas": nuevas}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en sincronización: {str(e)}"
        )

# === Función principal de sincronización con límite ===
def sincronizar_facturas_con_limite(user_id, gmail_token=None, max_emails=10):
    """
    Función de sincronización con límite de emails
    
    Args:
        user_id: ID del usuario
        gmail_token: Token de Gmail OAuth
        max_emails: Número máximo de emails a procesar
    """
    import time
    
    inicio_tiempo = time.time()
    
    try:
        print(f"🔄 Iniciando sincronización para usuario {user_id}")
        print(f"📧 Límite de emails: {max_emails}")
        print(f"⏱️ Tiempo estimado: {max_emails * 30} segundos")
        
        service = get_service(gmail_token)
        
        # Obtener links con límite
        links = get_edemsa_links(service, max_emails)
        
        if not links:
            return {
                "emails_procesados": max_emails,
                "facturas_encontradas": 0,
                "facturas_sincronizadas": 0,
                "tiempo_transcurrido": f"{time.time() - inicio_tiempo:.1f} segundos",
                "mensaje": "No se encontraron facturas en los emails procesados"
            }
        
        # APLICAR LÍMITE A LAS FACTURAS TAMBIÉN
        # Limitar las facturas a procesar basado en max_emails
        # Cada email debería tener aprox 1 factura, así que limitamos a max_emails facturas
        facturas_a_procesar = min(len(links), max_emails)
        links = links[:facturas_a_procesar]
        
        print(f"🔍 Encontradas {len(links)} facturas para descargar (limitado a {facturas_a_procesar})")
        
        nuevas = []
        facturas_procesadas = 0
        
        for i, link in enumerate(links):
            facturas_procesadas += 1
            print(f"📄 Descargando factura {facturas_procesadas}/{len(links)} (≈{facturas_procesadas * 30}s estimados)")
            
            factura = descargar_factura_pdf(link, i, user_id)
            if factura:
                nuevas.append({
                    "id": factura.id,
                    "nic": factura.nic,
                    "direccion": factura.direccion,
                    "fecha_lectura": factura.fecha_lectura,
                    "consumo_kwh": factura.consumo_kwh
                })
        
        tiempo_total = time.time() - inicio_tiempo
        
        resultado = {
            "emails_procesados": max_emails,
            "facturas_encontradas": facturas_a_procesar,  # Actualizado para reflejar el límite aplicado
            "facturas_sincronizadas": len(nuevas),
            "facturas": nuevas,
            "tiempo_transcurrido": f"{tiempo_total:.1f} segundos",
            "tiempo_promedio_por_factura": f"{tiempo_total/len(links):.1f} segundos" if links else "N/A",
            "rendimiento": "✅ Sincronización completada exitosamente",
            "limite_aplicado": f"Se limitó a {facturas_a_procesar} facturas basado en {max_emails} emails"
        }
        
        print(f"🎉 Sincronización completada: {len(nuevas)} facturas en {tiempo_total:.1f}s")
        print(f"📊 Límite respetado: {facturas_a_procesar} facturas procesadas de {len(links)} encontradas")
        
        return resultado
        
    except Exception as e:
        tiempo_error = time.time() - inicio_tiempo
        print(f"❌ Error en sincronización después de {tiempo_error:.1f}s: {str(e)}")
        
        return {
            "error": f"Error en sincronización: {str(e)}",
            "emails_procesados": 0,
            "facturas_sincronizadas": 0,
            "tiempo_transcurrido": f"{tiempo_error:.1f} segundos",
            "rendimiento": "❌ Error durante la sincronización"
        }