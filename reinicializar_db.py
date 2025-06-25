#!/usr/bin/env python3
"""
Script para reinicializar completamente la base de datos y limpiar cualquier referencia problemática
"""
import os
import sys
import sqlite3
import shutil
from datetime import datetime

# Agregar el directorio de la app al path
sys.path.append('/home/marcos/Escritorio/APP_E-Consumo')

def hacer_backup_completo():
    """Hacer backup completo antes de reinicializar"""
    if os.path.exists('consumo.db'):
        backup_name = f'consumo_full_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        shutil.copy2('consumo.db', backup_name)
        print(f"✅ Backup completo creado: {backup_name}")
        return backup_name
    return None

def recrear_base_datos_limpia():
    """Recrear la base de datos desde cero con solo las tablas necesarias"""
    print("🔄 RECREANDO BASE DE DATOS LIMPIA...")
    print("=" * 50)
    
    try:
        # Eliminar base de datos actual
        if os.path.exists('consumo.db'):
            os.remove('consumo.db')
            print("✅ Base de datos anterior eliminada")
        
        # Importar modelos limpios
        from app.db.base import Base
        from app.db.session import engine
        from app.models import factura_model, historico_model, user_model
        
        print("✅ Modelos importados correctamente")
        
        # Crear todas las tablas desde cero
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas creadas desde cero")
        
        # Verificar tablas creadas
        conn = sqlite3.connect('consumo.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Tablas creadas: {tablas}")
        
        for tabla in tablas:
            cursor.execute(f"PRAGMA table_info({tabla})")
            columns = cursor.fetchall()
            print(f"🔍 {tabla}: {len(columns)} columnas")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error recreando base de datos: {e}")
        return False

def restaurar_datos_esenciales(backup_file):
    """Restaurar solo los datos esenciales desde el backup"""
    if not backup_file or not os.path.exists(backup_file):
        print("⚠️ No hay backup para restaurar datos")
        return False
    
    print(f"\n📥 RESTAURANDO DATOS DESDE: {backup_file}")
    print("=" * 50)
    
    try:
        # Conectar a ambas bases de datos
        conn_backup = sqlite3.connect(backup_file)
        conn_nueva = sqlite3.connect('consumo.db')
        
        cursor_backup = conn_backup.cursor()
        cursor_nueva = conn_nueva.cursor()
        
        # Restaurar usuarios
        print("👥 Restaurando usuarios...")
        cursor_backup.execute("SELECT * FROM users")
        usuarios = cursor_backup.fetchall()
        
        for usuario in usuarios:
            cursor_nueva.execute('''
                INSERT INTO users (id, email, full_name, gmail_token, is_active, 
                                 created_at, updated_at, google_id, picture)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', usuario[:9])  # Solo las primeras 9 columnas (sin fcm_token)
        
        print(f"✅ {len(usuarios)} usuarios restaurados")
        
        # Restaurar facturas
        print("📄 Restaurando facturas...")
        cursor_backup.execute("SELECT * FROM facturas")
        facturas = cursor_backup.fetchall()
        
        for factura in facturas:
            cursor_nueva.execute('''
                INSERT INTO facturas (id, nic, direccion, fecha_lectura, 
                                    consumo_kwh, link, imagen, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', factura)
        
        print(f"✅ {len(facturas)} facturas restauradas")
        
        # Restaurar histórico
        print("📈 Restaurando histórico...")
        cursor_backup.execute("SELECT * FROM historico_consumo")
        historico = cursor_backup.fetchall()
        
        for registro in historico:
            cursor_nueva.execute('''
                INSERT INTO historico_consumo (id, fecha, consumo_kwh, factura_id)
                VALUES (?, ?, ?, ?)
            ''', registro)
        
        print(f"✅ {len(historico)} registros de histórico restaurados")
        
        # Confirmar cambios
        conn_nueva.commit()
        
        # Cerrar conexiones
        conn_backup.close()
        conn_nueva.close()
        
        print("✅ Todos los datos esenciales restaurados")
        return True
        
    except Exception as e:
        print(f"❌ Error restaurando datos: {e}")
        return False

def verificar_base_limpia():
    """Verificar que la base de datos está limpia y funcional"""
    print(f"\n🔍 VERIFICANDO BASE LIMPIA...")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('consumo.db')
        cursor = conn.cursor()
        
        # Verificar tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = [row[0] for row in cursor.fetchall()]
        
        tablas_esperadas = ['users', 'facturas', 'historico_consumo']
        
        print(f"📋 Tablas presentes: {tablas}")
        print(f"📋 Tablas esperadas: {tablas_esperadas}")
        
        if set(tablas) == set(tablas_esperadas):
            print("✅ Solo las tablas necesarias están presentes")
        else:
            print("⚠️ Tablas inesperadas encontradas")
        
        # Contar registros
        for tabla in tablas_esperadas:
            if tabla in tablas:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                print(f"📊 {tabla}: {count} registros")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verificando base: {e}")
        return False

def main():
    print("🚀 REINICIALIZACIÓN COMPLETA DE BASE DE DATOS")
    print("Este script recreará la base de datos desde cero eliminando cualquier referencia problemática")
    print()
    
    # Hacer backup
    backup_file = hacer_backup_completo()
    
    # Confirmar
    respuesta = input("¿Continuar con la reinicialización completa? (s/N): ").lower().strip()
    
    if respuesta in ['s', 'si', 'sí']:
        # Recrear base limpia
        if recrear_base_datos_limpia():
            # Restaurar datos
            if restaurar_datos_esenciales(backup_file):
                # Verificar resultado
                if verificar_base_limpia():
                    print(f"\n🎉 REINICIALIZACIÓN COMPLETADA EXITOSAMENTE!")
                    print(f"✅ Base de datos limpia y funcional")
                    print(f"💾 Backup disponible: {backup_file}")
                else:
                    print(f"\n⚠️ Reinicialización completada pero con advertencias")
            else:
                print(f"\n❌ Error restaurando datos")
        else:
            print(f"\n❌ Error recreando base de datos")
    else:
        print("❌ Operación cancelada")
        if backup_file:
            os.remove(backup_file)

if __name__ == "__main__":
    main()
