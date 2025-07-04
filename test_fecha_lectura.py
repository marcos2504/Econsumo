#!/usr/bin/env python3
"""
Script para probar la lógica de fecha_lectura en el servicio de notificaciones
"""

import sys
import os
from datetime import datetime, timedelta

# Agregar el directorio raíz al path
sys.path.append('/home/marcos/Escritorio/APP_E-Consumo')

from app.db.session import SessionLocal
from app.models.user_model import User
from app.models.factura_model import Factura
from app.services.notificaciones import notificacion_service
from sqlalchemy import desc

def verificar_fechas_facturas():
    """Verificar las fechas de facturas en la base de datos"""
    print("🔍 Verificando fechas de facturas en la base de datos...")
    
    db = SessionLocal()
    try:
        # Obtener usuarios con refresh token
        usuarios = notificacion_service.obtener_usuarios_con_refresh_token(db)
        print(f"👥 Usuarios con refresh token: {len(usuarios)}")
        
        for user in usuarios:
            print(f"\n👤 Usuario: {user.email} (ID: {user.id})")
            
            # Obtener todas las facturas del usuario ordenadas por fecha_lectura
            facturas = db.query(Factura).filter(
                Factura.user_id == user.id
            ).order_by(desc(Factura.fecha_lectura)).limit(5).all()
            
            print(f"📄 Facturas encontradas: {len(facturas)}")
            
            for i, factura in enumerate(facturas):
                print(f"  {i+1}. NIC: {factura.nic}")
                print(f"     Fecha lectura: {factura.fecha_lectura} (tipo: {type(factura.fecha_lectura)})")
                print(f"     Consumo: {factura.consumo_kwh} kWh")
                print(f"     ID: {factura.id}")
                print()
            
            # Probar la función de obtener última fecha
            print("🕒 Probando función obtener_ultima_fecha_lectura:")
            ultima_fecha = notificacion_service.obtener_ultima_fecha_lectura(db, user.id)
            print(f"   Resultado: {ultima_fecha}")
            print(f"   Tipo: {type(ultima_fecha)}")
            print(f"   Días desde ahora: {(datetime.now() - ultima_fecha).days}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def probar_busqueda_emails():
    """Probar la búsqueda de emails con la fecha correcta"""
    print("\n🔍 Probando búsqueda de emails...")
    
    db = SessionLocal()
    try:
        usuarios = notificacion_service.obtener_usuarios_con_refresh_token(db)
        
        if usuarios:
            user = usuarios[0]  # Tomar el primer usuario
            print(f"👤 Probando con usuario: {user.email}")
            
            # Obtener última fecha
            ultima_fecha = notificacion_service.obtener_ultima_fecha_lectura(db, user.id)
            print(f"📅 Buscando emails desde: {ultima_fecha}")
            
            # Buscar emails (esto puede tardar)
            links = notificacion_service.buscar_nuevos_emails(user, ultima_fecha, db)
            print(f"📧 Emails encontrados: {len(links)}")
            
            for i, link in enumerate(links[:3]):  # Mostrar solo los primeros 3
                print(f"  {i+1}. {link[:100]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Test de lógica de fecha_lectura")
    print("=" * 50)
    
    verificar_fechas_facturas()
    
    # Opcional: probar búsqueda de emails
    respuesta = input("\n¿Probar búsqueda de emails? (s/n): ")
    if respuesta.lower() == 's':
        probar_busqueda_emails()
    
    print("\n✅ Test completado")
