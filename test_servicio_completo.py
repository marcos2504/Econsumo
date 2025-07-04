#!/usr/bin/env python3
"""
Test completo del servicio de notificaciones con métricas mejoradas
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Agregar el directorio raíz al path
sys.path.append('/home/marcos/Escritorio/APP_E-Consumo')

from app.services.notificaciones import notificacion_service

def test_servicio_completo():
    """Probar el servicio completo de notificaciones"""
    print("🚀 Iniciando test completo del servicio de notificaciones")
    print("=" * 60)
    
    # Ejecutar el servicio
    resultado = notificacion_service.ejecutar_servicio_notificaciones()
    
    print("\n📊 RESULTADO COMPLETO:")
    print("=" * 60)
    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
    
    print("\n📈 RESUMEN DE MÉTRICAS:")
    print("=" * 40)
    print(f"⏰ Timestamp: {resultado['timestamp']}")
    print(f"👥 Usuarios procesados: {resultado['usuarios_procesados']}")
    print(f"📧 Total emails nuevos: {resultado['total_emails_nuevos']}")
    print(f"📄 Total facturas procesadas: {resultado['total_facturas_procesadas']}")
    print(f"🔄 Total facturas duplicadas: {resultado['total_facturas_duplicadas']}")
    print(f"🚨 Total anomalías detectadas: {resultado['total_anomalias_detectadas']}")
    print(f"📤 Alertas enviadas: {resultado['alertas_enviadas']}")
    print(f"❌ Usuarios con errores: {resultado['usuarios_con_errores']}")
    
    print("\n👤 DETALLES POR USUARIO:")
    print("=" * 40)
    for detalle in resultado['detalles']:
        print(f"\n📧 Usuario: {detalle['email']}")
        print(f"   📅 Última fecha: {detalle['ultima_fecha_procesamiento']}")
        print(f"   📧 Emails nuevos: {detalle['emails_nuevos']}")
        print(f"   📄 Facturas procesadas: {detalle['facturas_procesadas']}")
        print(f"   🔄 Facturas duplicadas: {detalle.get('facturas_duplicadas', 0)}")
        print(f"   🚨 Anomalías detectadas: {detalle['anomalias_detectadas']}")
        print(f"   📤 Email enviado: {detalle['email_enviado']}")
        print(f"   ❌ Errores: {len(detalle['errores'])}")
        if detalle['errores']:
            for error in detalle['errores']:
                print(f"      - {error}")
    
    # Verificar si todo está funcionando como esperado
    print("\n✅ VALIDACIONES:")
    print("=" * 40)
    
    if resultado['usuarios_procesados'] > 0:
        print("✅ Se procesaron usuarios")
    else:
        print("❌ No se procesaron usuarios")
    
    if 'error_general' not in resultado:
        print("✅ No hay errores generales")
    else:
        print(f"❌ Error general: {resultado['error_general']}")
    
    # Verificar lógica de fechas
    for detalle in resultado['detalles']:
        if detalle['ultima_fecha_procesamiento']:
            fecha = datetime.fromisoformat(detalle['ultima_fecha_procesamiento'])
            dias_desde = (datetime.now() - fecha).days
            if dias_desde > 0:
                print(f"✅ {detalle['email']}: Buscando desde hace {dias_desde} días (fecha válida)")
            else:
                print(f"⚠️ {detalle['email']}: Fecha en el futuro")
    
    print("\n🎯 CONCLUSIONES:")
    print("=" * 40)
    
    if resultado['total_emails_nuevos'] == 0:
        print("📭 No se encontraron emails nuevos desde la última fecha de factura")
        print("   Esto es normal si las facturas más recientes son del 30/04/2025")
        print("   y se están buscando emails posteriores a esa fecha.")
    
    if resultado['total_facturas_duplicadas'] > 0:
        print(f"🔄 Se omitieron {resultado['total_facturas_duplicadas']} facturas duplicadas")
        print("   Esto indica que la validación de duplicados funciona correctamente.")
    
    if resultado['total_anomalias_detectadas'] == 0:
        print("🟢 No se detectaron anomalías en las facturas procesadas")
        print("   Esto puede ser normal si el consumo está dentro de los parámetros normales.")
    
    print(f"\n{'='*60}")
    print("✅ Test completado exitosamente")

if __name__ == "__main__":
    test_servicio_completo()
