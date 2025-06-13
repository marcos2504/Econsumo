#!/usr/bin/env python3
"""
Script para limpiar cache y probar credenciales frescas
"""
import os
import sys
import subprocess
import requests
from dotenv import load_dotenv

def clear_python_cache():
    """Limpiar cache de Python"""
    print("🧹 LIMPIANDO CACHE DE PYTHON...")
    
    # Limpiar __pycache__ directories
    for root, dirs, files in os.walk('.'):
        for dir in dirs:
            if dir == '__pycache__':
                cache_path = os.path.join(root, dir)
                print(f"  Eliminando: {cache_path}")
                subprocess.run(['rm', '-rf', cache_path], capture_output=True)
    
    # Limpiar archivos .pyc
    subprocess.run(['find', '.', '-name', '*.pyc', '-delete'], capture_output=True)
    print("✅ Cache de Python limpiado")

def clear_environment_variables():
    """Limpiar variables de entorno en memoria"""
    print("\n🔄 LIMPIANDO VARIABLES DE ENTORNO...")
    
    # Variables de Google que queremos limpiar
    google_vars = [
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'GOOGLE_APPLICATION_CREDENTIALS'
    ]
    
    for var in google_vars:
        if var in os.environ:
            print(f"  Eliminando variable: {var}")
            del os.environ[var]
    
    print("✅ Variables de entorno limpiadas")

def reload_fresh_env():
    """Recargar variables de entorno frescas"""
    print("\n📁 CARGANDO VARIABLES FRESCAS DESDE .ENV...")
    
    # Forzar recarga completa
    load_dotenv(override=True)
    
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    
    print(f"✅ GOOGLE_CLIENT_ID cargado: {client_id}")
    print(f"✅ GOOGLE_CLIENT_SECRET cargado: {client_secret}")
    
    return client_id, client_secret

def test_fresh_credentials(client_id, client_secret):
    """Probar credenciales recién cargadas"""
    print(f"\n🧪 PROBANDO CREDENCIALES FRESCAS...")
    print("=" * 50)
    
    # Test directo con Google OAuth
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': 'test_invalid_code_fresh',
        'grant_type': 'authorization_code'
    }
    
    try:
        response = requests.post('https://oauth2.googleapis.com/token', data=data, timeout=10)
        print(f"📡 Status Code: {response.status_code}")
        
        if response.status_code == 400:
            error_data = response.json()
            error_type = error_data.get('error')
            
            if error_type == 'invalid_grant':
                print("✅ CREDENCIALES VÁLIDAS - Error esperado por código inválido")
                print("🎉 Las credenciales funcionan correctamente con Google")
                return True
            elif error_type == 'invalid_client':
                print("❌ CREDENCIALES INVÁLIDAS - Google las rechaza")
                print(f"📄 Detalle: {error_data.get('error_description', 'N/A')}")
                return False
            else:
                print(f"⚠️ Error inesperado: {error_type}")
                
        elif response.status_code == 401:
            print("❌ 401 Unauthorized - Credenciales rechazadas")
            try:
                error_data = response.json()
                print(f"📄 Detalle: {error_data}")
            except:
                pass
            return False
        else:
            print(f"⚠️ Status inesperado: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
    
    return False

def show_current_env_file():
    """Mostrar contenido actual del archivo .env"""
    print(f"\n📄 CONTENIDO ACTUAL DEL ARCHIVO .ENV:")
    print("=" * 50)
    
    try:
        with open('.env', 'r') as f:
            content = f.read()
            for line in content.split('\n'):
                if 'GOOGLE_CLIENT' in line and not line.startswith('#'):
                    print(f"  {line}")
    except Exception as e:
        print(f"❌ Error leyendo .env: {e}")

if __name__ == "__main__":
    print("🚀 LIMPIANDO CACHE Y PROBANDO CREDENCIALES FRESCAS")
    print()
    
    # Paso 1: Mostrar archivo .env actual
    show_current_env_file()
    
    # Paso 2: Limpiar cache
    clear_python_cache()
    clear_environment_variables()
    
    # Paso 3: Recargar variables frescas
    client_id, client_secret = reload_fresh_env()
    
    # Paso 4: Probar credenciales
    if client_id and client_secret:
        credentials_ok = test_fresh_credentials(client_id, client_secret)
        
        print(f"\n" + "=" * 50)
        if credentials_ok:
            print("✅ RESULTADO: ¡Las credenciales funcionan!")
            print("🎉 Puedes usar estas credenciales en tu servidor")
            print("🔄 Reinicia el servidor para cargar las credenciales limpias")
        else:
            print("❌ RESULTADO: Las credenciales aún no funcionan")
            print("🔧 Verifica la configuración en Google Cloud Console")
    else:
        print("❌ No se pudieron cargar las credenciales desde .env")
    
    print(f"\n💡 PRÓXIMO PASO:")
    print("Si las credenciales funcionan, reinicia el servidor FastAPI para que cargue las credenciales limpias")