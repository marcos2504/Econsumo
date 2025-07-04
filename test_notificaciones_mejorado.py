#!/usr/bin/env python3
"""
Script para probar el servicio de notificaciones mejorado

Este script:
1. Verifica usuarios con refresh token
2. Ejecuta el servicio mejorado de notificaciones
3. Muestra métricas detalladas y el resultado
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
from app.models.factura_model import Factura
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
            
            # Mostrar última factura procesada
            ultima_factura = db.query(Factura).filter(
                Factura.user_id == usuario.id
            ).order_by(Factura.created_at.desc()).first()
            
            if ultima_factura:
                print(f"    - Última factura: {ultima_factura.created_at.strftime('%Y-%m-%d %H:%M')} (NIC: {ultima_factura.nic})")
            else:
                print(f"    - Última factura: ❌ No hay facturas")
            print()
        
        return usuarios
        
    except Exception as e:
        print(f"❌ Error verificando usuarios: {str(e)}")
        return []
    finally:
        db.close()

def mostrar_resumen_facturas():
    """Mostrar resumen de facturas en la base de datos"""
    print("📊 Resumen de facturas en la base de datos:")
    
    db = SessionLocal()
    try:
        # Total de facturas
        total_facturas = db.query(Factura).count()
        print(f"  • Total de facturas: {total_facturas}")
        
        # Facturas por usuario
        usuarios_con_facturas = db.query(User).join(Factura).distinct().all()
        print(f"  • Usuarios con facturas: {len(usuarios_con_facturas)}")
        
        for user in usuarios_con_facturas:
            count = db.query(Factura).filter(Factura.user_id == user.id).count()
            ultima = db.query(Factura).filter(Factura.user_id == user.id).order_by(Factura.created_at.desc()).first()
            print(f"    - {user.email}: {count} facturas (última: {ultima.created_at.strftime('%Y-%m-%d') if ultima else 'N/A'})")
        
        print()
        
    except Exception as e:
        print(f"❌ Error obteniendo resumen de facturas: {str(e)}")
    finally:
        db.close()

def ejecutar_servicio_notificaciones():
    """Ejecutar el servicio de notificaciones mejorado"""
    print("🚀 Ejecutando servicio de notificaciones mejorado...")
    print(f"⏰ Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    try:
        # Ejecutar el servicio
        resultado = notificacion_service.ejecutar_servicio_notificaciones()
        
        print("📋 RESULTADO DEL SERVICIO:")
        print(f"  • Timestamp: {resultado['timestamp']}")
        print(f"  • Usuarios procesados: {resultado['usuarios_procesados']}")
        print(f"  • Total emails nuevos: {resultado['total_emails_nuevos']}")
        print(f"  • Total facturas procesadas: {resultado['total_facturas_procesadas']}")
        print(f"  • Total facturas duplicadas: {resultado['total_facturas_duplicadas']}")
        print(f"  • Total anomalías detectadas: {resultado['total_anomalias_detectadas']}")
        print(f"  • Alertas enviadas: {resultado['alertas_enviadas']}")
        print(f"  • Usuarios con errores: {resultado['usuarios_con_errores']}")
        print()
        
        # Mostrar detalles por usuario
        if resultado['detalles']:
            print("👥 DETALLES POR USUARIO:")
            for detalle in resultado['detalles']:
                print(f"  📧 {detalle['email']}:")
                print(f"    - Última fecha procesamiento: {detalle.get('ultima_fecha_procesamiento', 'N/A')}")
                print(f"    - Emails nuevos encontrados: {detalle['emails_nuevos']}")
                print(f"    - Facturas procesadas: {detalle['facturas_procesadas']}")
                print(f"    - Facturas duplicadas: {detalle.get('facturas_duplicadas', 0)}")
                print(f"    - Anomalías detectadas: {detalle['anomalias_detectadas']}")
                print(f"    - Email enviado: {'✅ Sí' if detalle['email_enviado'] else '❌ No'}")
                
                if detalle['errores']:
                    print(f"    - Errores: {', '.join(detalle['errores'])}")
                print()
        
        return resultado
        
    except Exception as e:
        print(f"❌ Error ejecutando servicio: {str(e)}")
        return {"error": str(e)}

def main():
    """Función principal"""
    print("🎯 SERVICIO DE NOTIFICACIONES E-CONSUMO (MEJORADO)")
    print("=" * 60)
    print()
    
    # 1. Verificar usuarios con refresh token
    usuarios = verificar_usuarios_con_refresh_token()
    
    if not usuarios:
        print("⚠️ No hay usuarios con refresh token configurado.")
        print("💡 Los usuarios deben autorizar el acceso a Gmail primero.")
        return
    
    # 2. Mostrar resumen de facturas
    mostrar_resumen_facturas()
    
    # 3. Ejecutar servicio
    resultado = ejecutar_servicio_notificaciones()
    
    # 4. Resumen final
    print("=" * 60)
    print("📊 RESUMEN FINAL:")
    
    if 'error' in resultado:
        print(f"❌ Error general: {resultado['error']}")
    else:
        exito = resultado.get('alertas_enviadas', 0) > 0
        facturas_nuevas = resultado.get('total_facturas_procesadas', 0)
        facturas_duplicadas = resultado.get('total_facturas_duplicadas', 0)
        
        print(f"✅ Servicio {'exitoso' if exito else 'completado'}")
        print(f"📧 Alertas enviadas: {resultado.get('alertas_enviadas', 0)}")
        print(f"📄 Facturas nuevas procesadas: {facturas_nuevas}")
        print(f"🔄 Facturas duplicadas omitidas: {facturas_duplicadas}")
        
        if resultado.get('total_anomalias_detectadas', 0) > 0:
            print(f"⚠️ Anomalías detectadas: {resultado['total_anomalias_detectadas']}")
        else:
            print("✅ No se detectaron anomalías")
    
    print()
    print("🏁 Test completado.")

if __name__ == "__main__":
    # Ejecutar el script principal
    main()
