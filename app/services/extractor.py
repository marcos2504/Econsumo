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
def get_service(gmail_token=None):
    """
    Obtener servicio de Gmail usando token OAuth o archivo token.json
    """
    try:
        if gmail_token:
            # Usar token OAuth directamente
            creds = Credentials(
                token=gmail_token,
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

def get_edemsa_links(service):
    results = service.users().messages().list(userId='me', q=EMAIL_QUERY).execute()
    messages = results.get('messages', [])
    links = []

    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        html_data = get_html_part(msg_data['payload'])
        if not html_data:
            continue
        html = base64.urlsafe_b64decode(html_data + '===').decode('utf-8', errors='ignore')
        encontrados = re.findall(r'https://oficinavirtual\.edemsa\.com/facturad\.php\?conf=[^"]+', html)
        links.extend(encontrados)

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
                    db.commit()

                db.close()
                return factura
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