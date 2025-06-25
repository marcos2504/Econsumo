#!/usr/bin/env python3
"""
Script para detectar problemas en los modelos después de eliminar tablas
"""
import sys
import os

# Agregar el directorio de la app al path
sys.path.append('/home/marcos/Escritorio/APP_E-Consumo')

def test_model_imports():
    """Probar imports de modelos individualmente"""
    print("🔍 PROBANDO IMPORTS DE MODELOS...")
    print("=" * 50)
    
    try:
        print("📋 Importando factura_model...")
        from app.models import factura_model
        print("✅ factura_model importado correctamente")
    except Exception as e:
        print(f"❌ Error en factura_model: {e}")
        return False
    
    try:
        print("📋 Importando user_model...")
        from app.models import user_model
        print("✅ user_model importado correctamente")
    except Exception as e:
        print(f"❌ Error en user_model: {e}")
        return False
    
    try:
        print("📋 Importando historico_model...")
        from app.models import historico_model
        print("✅ historico_model importado correctamente")
    except Exception as e:
        print(f"❌ Error en historico_model: {e}")
        return False
    
    return True

def test_base_creation():
    """Probar creación de Base y tablas"""
    print("\n🔧 PROBANDO CREACIÓN DE BASE...")
    print("=" * 50)
    
    try:
        from app.db.base import Base
        from app.db.session import engine
        print("✅ Base y engine importados correctamente")
        
        # Intentar crear las tablas
        print("🔄 Creando metadatos...")
        Base.metadata.create_all(bind=engine)
        print("✅ Metadatos creados sin errores")
        
        return True
    except Exception as e:
        print(f"❌ Error creando Base: {e}")
        return False

def test_relationships():
    """Probar relaciones entre modelos"""
    print("\n🔗 PROBANDO RELACIONES...")
    print("=" * 50)
    
    try:
        from app.models.factura_model import Factura
        from app.models.user_model import User
        from app.models.historico_model import HistoricoConsumo
        
        print("✅ Todas las clases importadas correctamente")
        
        # Verificar que las relaciones estén definidas correctamente
        print("🔍 Verificando relaciones de User...")
        if hasattr(User, 'facturas'):
            print("✅ User tiene relación 'facturas'")
        else:
            print("⚠️ User no tiene relación 'facturas'")
        
        print("🔍 Verificando relaciones de Factura...")
        if hasattr(Factura, 'user'):
            print("✅ Factura tiene relación 'user'")
        else:
            print("⚠️ Factura no tiene relación 'user'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en relaciones: {e}")
        return False

def main():
    print("🚀 DIAGNÓSTICO DE MODELOS DESPUÉS DE ELIMINAR TABLAS")
    print("Buscando problemas con referencias a 'Notificacion'...")
    print()
    
    success = True
    
    # Test 1: Imports
    if not test_model_imports():
        success = False
    
    # Test 2: Base creation
    if not test_base_creation():
        success = False
    
    # Test 3: Relationships  
    if not test_relationships():
        success = False
    
    print(f"\n" + "=" * 50)
    if success:
        print("✅ TODOS LOS TESTS PASARON")
        print("🎯 Los modelos están funcionando correctamente")
    else:
        print("❌ SE DETECTARON PROBLEMAS")
        print("🔧 Revisa los errores arriba para solucionarlos")

if __name__ == "__main__":
    main()
