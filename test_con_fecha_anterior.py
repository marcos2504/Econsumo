#!/usr/bin/env python3
"""
Test del servicio con fecha modificada para encontrar emails y probar alertas
"""

import sys
from datetime import datetime, timedelta

sys.path.append('/home/marcos/Escritorio/APP_E-Consumo')

from app.services.notificaciones import notificacion_service

# Modificar temporalmente el método para buscar desde hace más tiempo
def test_con_fecha_anterior():
    """Test buscando emails desde hace más tiempo para encontrar emails"""
    print("🧪 Test con fecha anterior para encontrar emails...")
    
    # Backup del método original
    metodo_original = notificacion_service.obtener_ultima_fecha_lectura
    
    # Método modificado que busca desde hace 90 días
    def obtener_fecha_anterior(db, user_id):
        return datetime.now() - timedelta(days=90)
    
    try:
        # Aplicar método modificado temporalmente
        notificacion_service.obtener_ultima_fecha_lectura = obtener_fecha_anterior
        
        print("📅 Buscando emails desde hace 90 días...")
        resultado = notificacion_service.ejecutar_servicio_notificaciones()
        
        print(f"\n📊 Resultado con fecha anterior:")
        print(f"   📧 Emails encontrados: {resultado['total_emails_nuevos']}")
        print(f"   📄 Facturas procesadas: {resultado['total_facturas_procesadas']}")
        print(f"   🚨 Anomalías detectadas: {resultado['total_anomalias_detectadas']}")
        print(f"   📤 Alertas enviadas: {resultado['alertas_enviadas']}")
        
    finally:
        # Restaurar método original
        notificacion_service.obtener_ultima_fecha_lectura = metodo_original

if __name__ == "__main__":
    test_con_fecha_anterior()
