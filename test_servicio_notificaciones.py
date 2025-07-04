#!/usr/bin/env python3
"""
Script para probar y ejecutar el servicio de notificaciones existente

Este script:
1. Verifica que usuarios tienen refresh token
2. Ejecuta el monitoreo para todos los usuarios
3. Muestra el resultado del proceso
"""

import sys
import os
from datetime import datetime

# Agregar el path del proyecto
sys.path.append('/home/marcos/Escritorio/APP_E-Consumo')

from dotenv import load_dotenv
load_dotenv()

from app.db.session import SessionLocal
from app.models.user_model import User
from app.services.notificaciones import notificacion_service

def verificar_usuarios_con_refresh_token():
    """Verificar usuarios que tienen refresh token configurado"""
    print("🔍 Verificando usuarios con refresh token...")
    
    db = SessionLocal()
    try:
        usuarios = db.query(User).filter(
            User.gmail_refresh_token.isnot(None),
            User.gmail_refresh_token != "",
            User.is_active == True
        ).all()
        
        print(f"📊 Encontrados {len(usuarios)} usuarios con refresh token:")
        for usuario in usuarios:
            print(f"  • {usuario.email} (ID: {usuario.id})")
            print(f"    - Refresh token: {'✅ Configurado' if usuario.gmail_refresh_token else '❌ No configurado'}")
            print(f"    - Access token: {'✅ Presente' if usuario.gmail_token else '❌ Ausente'}")
            print(f"    - Activo: {'✅ Sí' if usuario.is_active else '❌ No'}")
            print()
        
        return usuarios
        
    except Exception as e:
        print(f"❌ Error verificando usuarios: {str(e)}")
        return []
    finally:
        db.close()

def ejecutar_monitoreo_completo():
    """Ejecutar el monitoreo completo usando el servicio unificado"""
    print("🚀 Iniciando monitoreo completo de notificaciones...")
    print(f"⏰ Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    try:
        # Ejecutar el servicio unificado
        resultado = notificacion_service.ejecutar_servicio_notificaciones()
        
        print("📋 Resultado del monitoreo:")
        print(f"  • Usuarios procesados: {resultado.get('usuarios_procesados', 0)}")
        print(f"  • Total emails nuevos: {resultado.get('total_emails_nuevos', 0)}")
        print(f"  • Total facturas procesadas: {resultado.get('total_facturas_procesadas', 0)}")
        print(f"  • Total facturas duplicadas: {resultado.get('total_facturas_duplicadas', 0)}")
        print(f"  • Total anomalías detectadas: {resultado.get('total_anomalias_detectadas', 0)}")
        print(f"  • Alertas enviadas: {resultado.get('alertas_enviadas', 0)}")
        print(f"  • Usuarios con errores: {resultado.get('usuarios_con_errores', 0)}")
        print()
        
        # Mostrar detalles por usuario
        if 'detalles' in resultado:
            print("👥 Detalles por usuario:")
            for detalle in resultado['detalles']:
                print(f"  📧 {detalle.get('email', 'Usuario desconocido')}:")
                print(f"    - Emails nuevos: {detalle.get('emails_nuevos', 0)}")
                print(f"    - Facturas procesadas: {detalle.get('facturas_procesadas', 0)}")
                print(f"    - Facturas duplicadas: {detalle.get('facturas_duplicadas', 0)}")
                print(f"    - Anomalías detectadas: {detalle.get('anomalias_detectadas', 0)}")
                print(f"    - Email enviado: {detalle.get('email_enviado', False)}")
                if detalle.get('errores'):
                    print(f"    - Errores: {detalle['errores']}")
                print()
        
        return resultado
        
    except Exception as e:
        print(f"❌ Error durante el monitoreo: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

def mostrar_estado_servicio():
    """Mostrar el estado actual del servicio"""
    print("📊 Estado del servicio de notificaciones:")
    
    try:
        # Como el nuevo servicio es más simple, mostramos información básica
        db = SessionLocal()
        try:
            usuarios = notificacion_service.obtener_usuarios_con_refresh_token(db)
            print(f"  • Usuarios con refresh token: {len(usuarios)}")
            for user in usuarios:
                print(f"    - {user.email} (ID: {user.id})")
        finally:
            db.close()
        
    except Exception as e:
        print(f"  ❌ Error obteniendo estado: {str(e)}")

def main():
    """Función principal"""
    print("🎯 SERVICIO DE NOTIFICACIONES E-CONSUMO")
    print("=" * 60)
    print()
    
    # 1. Verificar usuarios con refresh token
    usuarios = verificar_usuarios_con_refresh_token()
    
    if not usuarios:
        print("⚠️ No hay usuarios con refresh token configurado.")
        print("💡 Los usuarios deben autorizar el acceso a Gmail primero.")
        return
    
    print()
    
    # 2. Mostrar estado del servicio
    mostrar_estado_servicio()
    
    # 3. Ejecutar monitoreo
    resultado = ejecutar_monitoreo_completo()
    
    # 4. Resumen final
    print("=" * 60)
    print("📊 RESUMEN FINAL:")
    
    if 'error' in resultado:
        print(f"❌ Error general: {resultado['error']}")
    else:
        exito = resultado.get('emails_enviados', 0) > 0
        print(f"✅ Monitoreo {'exitoso' if exito else 'completado'}")
        print(f"📧 Alertas enviadas: {resultado.get('emails_enviados', 0)}")
        
        if resultado.get('total_anomalias_detectadas', 0) > 0:
            print(f"⚠️ Anomalías detectadas: {resultado['total_anomalias_detectadas']}")
        else:
            print("✅ No se detectaron anomalías")
    
    print()
    print("🏁 Servicio completado.")

if __name__ == "__main__":
    # Ejecutar el script principal
    main()
