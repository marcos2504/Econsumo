import pandas as pd
import re
import google.generativeai as genai
from pdf2image import convert_from_path
from PIL import Image

# Configurar Gemini
genai.configure(api_key="AIzaSyD7ZiFXkHuT-npzaoSX8HPogB9zjwh_jfk")  # Reemplazá esto con tu clave real
modelo = genai.GenerativeModel("gemini-1.5-flash")

def extraer_grafico(nombre_pdf, output_path, dpi=200):
    try:
        pages = convert_from_path(nombre_pdf, dpi=dpi)
        if not pages:
            print("No se pudo renderizar el PDF.")
            return False
        page = pages[0]
        width, height = page.size
        top = int(height * 0.455)
        bottom = int(height * 0.585)
        left = int(width * 0.05)
        right = int(width * 0.495)
        grafico = page.crop((left, top, right, bottom))
        grafico.save(output_path)
        return True
    except Exception as e:
        print(f"[!] Error al extraer gráfico: {e}")
        return False

def analizar_con_gemini(nombre_imagen):
    prompt = (
        "Observá este gráfico de barras titulado 'HISTÓRICO DE CONSUMO'. El eje X muestra fechas (mes/año) y el eje Y muestra consumo eléctrico en KWh,"
        "Estimá visualmente el consumo de cada barra y devolvé una tabla con dos columnas: Fecha y Consumo (KWh). "
        "Usá como guía los valores del eje Y. Escribí la tabla con una fila por barra, sin texto adicional. Formato:\n"
        "Fecha | Consumo (KWh)\n"
    )
    try:
        with open(nombre_imagen, "rb") as f:
            image_bytes = f.read()
        response = modelo.generate_content([
            prompt,
            {
                "mime_type": "image/png",
                "data": image_bytes,
            }
        ])
        texto = response.text.strip()
        return parse_gemini_output(texto)
    except Exception as e:
        print(f"[!] Error con Gemini: {e}")
        return pd.DataFrame()

def parse_gemini_output(texto):
    lineas = texto.strip().splitlines()
    datos = []
    for linea in lineas:
        if re.match(r"\d{2}/\d{2} *\| *\d+", linea):
            partes = [p.strip() for p in linea.split("|")]
            if len(partes) == 2:
                try:
                    datos.append({"fecha": partes[0], "consumo_wh": int(partes[1])})
                except ValueError:
                    continue
    return pd.DataFrame(datos)
