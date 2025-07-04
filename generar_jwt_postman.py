#!/usr/bin/env python3
"""
Script para generar JWT directamente para pruebas en Postman
"""
import sqlite3
import sys
import os

# Agregar el directorio de la app al path
sys.path.append('/home/marcos/Escritorio/APP_E-Consumo')

from app.services.jwt_service import create_access_token

def generar_jwt_para_usuario(email):
    """Generar JWT directamente para un usuario existente"""
    
    print(f"🔑 GENERANDO JWT PARA: {email}")
    print("=" * 50)
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect('consumo.db')
        cursor = conn.cursor()
        
        # Buscar el usuario
        cursor.execute("SELECT id, email, gmail_token FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ Usuario no encontrado: {email}")
            return None
            
        user_id, user_email, gmail_token = user
        
        print(f"✅ Usuario encontrado: {user_email}")
        print(f"📧 ID: {user_id}")
        print(f"🔐 Gmail Token: {'SÍ' if gmail_token else 'NO'}")
        
        if gmail_token:
            print(f"🔐 Gmail Token: {gmail_token[:50]}...")
        
        # Generar JWT
        jwt_token = create_access_token(
            data={"sub": user_email, "user_id": user_id}
        )
        
        print(f"\n🎉 JWT GENERADO EXITOSAMENTE!")
        print(f"🔐 JWT Token: {jwt_token}")
        print(f"\n📋 COPIA ESTE TOKEN PARA POSTMAN:")
        print("-" * 50)
        print(jwt_token)
        print("-" * 50)
        
        conn.close()
        return jwt_token
        
    except Exception as e:
        print(f"❌ Error generando JWT: {e}")
        return None

def mostrar_instrucciones_postman(jwt_token):
    """Mostrar instrucciones para usar en Postman"""
    
    print(f"\n📬 INSTRUCCIONES PARA POSTMAN:")
    print("=" * 50)
    print(f"🌐 URL: http://localhost:8000/facturas/sync")
    print(f"📤 Método: POST")
    print(f"🔑 Authorization: Bearer Token")
    print(f"🎫 Token: {jwt_token}")
    print()
    print(f"📋 PASOS EN POSTMAN:")
    print("1. Crear nueva request POST")
    print("2. URL: http://localhost:8000/facturas/sync")
    print("3. Ir a 'Authorization' tab")
    print("4. Type: 'Bearer Token'")
    print("5. Token: pegar el JWT de arriba")
    print("6. Clic en 'Send'")
    print()
    print(f"✅ RESULTADO ESPERADO:")
    print("- Status: 200 OK")
    print("- Response: JSON con facturas sincronizadas desde Gmail")

def verificar_estado_sistema():
    """Verificar que todo esté listo para la prueba"""
    
    print(f"🔍 VERIFICANDO ESTADO DEL SISTEMA...")
    print("=" * 50)
    
    # Verificar base de datos
    try:
        conn = sqlite3.connect('consumo.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"👥 Usuarios en BD: {user_count}")
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE gmail_token IS NOT NULL")
        users_with_gmail = cursor.fetchone()[0]
        print(f"🔐 Usuarios con Gmail token: {users_with_gmail}")
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE gmail_refresh_token IS NOT NULL")
        users_with_refresh = cursor.fetchone()[0]
        print(f"🔄 Usuarios con Refresh token: {users_with_refresh}")
        
        # Mostrar detalles de tokens por usuario
        cursor.execute("""
            SELECT email, 
                   gmail_token IS NOT NULL as tiene_gmail,
                   gmail_refresh_token IS NOT NULL as tiene_refresh
            FROM users 
            WHERE gmail_token IS NOT NULL OR gmail_refresh_token IS NOT NULL
        """)
        users_tokens = cursor.fetchall()
        
        if users_tokens:
            print("\n📊 DETALLE DE TOKENS POR USUARIO:")
            for email, tiene_gmail, tiene_refresh in users_tokens:
                gmail_status = "✅" if tiene_gmail else "❌"
                refresh_status = "✅" if tiene_refresh else "❌"
                print(f"  {email}: Gmail {gmail_status} | Refresh {refresh_status}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error verificando BD: {e}")
    
    # Verificar servidor
    import requests
    try:
        response = requests.get("http://localhost:8000/auth/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Servidor corriendo: OK")
        else:
            print(f"⚠️ Servidor responde con: {response.status_code}")
    except Exception as e:
        print(f"❌ Servidor no accesible: {e}")

if __name__ == "__main__":
    print("🚀 GENERADOR DE JWT PARA POSTMAN")
    print()
    
    # Verificar estado del sistema
    verificar_estado_sistema()
    
    # Generar JWT para el usuario
    email = "marcosibarra1234@gmail.com"
    jwt_token = generar_jwt_para_usuario(email)
    
    if jwt_token:
        mostrar_instrucciones_postman(jwt_token)
        
        # Guardar en archivo para fácil acceso
        with open('jwt_for_postman.txt', 'w') as f:
            f.write(jwt_token)
        print(f"\n💾 JWT guardado en: jwt_for_postman.txt")
        
    else:
        print("❌ No se pudo generar JWT")
        print("🔧 Verifica que el usuario exista en la base de datos")