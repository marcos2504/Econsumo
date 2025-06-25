#!/usr/bin/env python3
"""
Script para eliminar las tablas agregadas recientemente y revertir cambios
"""
import sqlite3
import os
import shutil
from datetime import datetime

def hacer_backup():
    """Hacer backup de la base de datos antes de los cambios"""
    if os.path.exists('consumo.db'):
        backup_name = f'consumo_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        shutil.copy2('consumo.db', backup_name)
        print(f"✅ Backup creado: {backup_name}")
        return backup_name
    return None

def eliminar_tablas_agregadas():
    """Eliminar las tablas que fueron agregadas recientemente"""
    conn = sqlite3.connect('consumo.db')
    cursor = conn.cursor()
    
    # Lista de tablas a eliminar
    tablas_a_eliminar = [
        'notificaciones',
        'procesamiento_facturas', 
        'sincronizaciones',
        'user_nics'
    ]
    
    try:
        print("🗑️  ELIMINANDO TABLAS AGREGADAS RECIENTEMENTE...")
        print("=" * 50)
        
        for tabla in tablas_a_eliminar:
            try:
                # Verificar si la tabla existe
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,))
                if cursor.fetchone():
                    cursor.execute(f"DROP TABLE {tabla}")
                    print(f"✅ Tabla '{tabla}' eliminada")
                else:
                    print(f"ℹ️  Tabla '{tabla}' no existe")
            except Exception as e:
                print(f"❌ Error eliminando tabla '{tabla}': {e}")
        
        print("\n🔧 ELIMINANDO COLUMNAS AGREGADAS...")
        print("=" * 50)
        
        # Eliminar columna fcm_token de users si existe
        try:
            # Verificar si existe la columna fcm_token
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'fcm_token' in column_names:
                print("🔄 Eliminando columna 'fcm_token' de tabla 'users'...")
                
                # Crear tabla temporal sin fcm_token
                cursor.execute('''
                    CREATE TABLE users_temp (
                        id INTEGER PRIMARY KEY,
                        email VARCHAR UNIQUE NOT NULL,
                        full_name VARCHAR,
                        gmail_token TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at DATETIME,
                        updated_at DATETIME,
                        google_id VARCHAR UNIQUE,
                        picture VARCHAR
                    )
                ''')
                
                # Copiar datos (excluyendo fcm_token)
                cursor.execute('''
                    INSERT INTO users_temp (id, email, full_name, gmail_token, is_active, 
                                          created_at, updated_at, google_id, picture)
                    SELECT id, email, full_name, gmail_token, is_active, 
                           created_at, updated_at, google_id, picture
                    FROM users
                ''')
                
                # Eliminar tabla original y renombrar temporal
                cursor.execute('DROP TABLE users')
                cursor.execute('ALTER TABLE users_temp RENAME TO users')
                
                print("✅ Columna 'fcm_token' eliminada de tabla 'users'")
            else:
                print("ℹ️  Columna 'fcm_token' no existe en tabla 'users'")
                
        except Exception as e:
            print(f"❌ Error eliminando columna fcm_token: {e}")
        
        conn.commit()
        print("\n🎉 PROCESO DE LIMPIEZA COMPLETADO!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error general: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verificar_estructura_final():
    """Verificar que las tablas fueron eliminadas correctamente"""
    conn = sqlite3.connect('consumo.db')
    cursor = conn.cursor()
    
    try:
        print("\n📋 VERIFICANDO ESTRUCTURA FINAL...")
        print("=" * 50)
        
        # Listar tablas restantes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas_restantes = [row[0] for row in cursor.fetchall()]
        
        print("✅ TABLAS RESTANTES:")
        for tabla in tablas_restantes:
            print(f"  - {tabla}")
        
        # Verificar estructura de tabla users
        print(f"\n🔍 ESTRUCTURA FINAL DE 'users':")
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]}) - PK: {col[5]}, NotNull: {col[3]}")
        
        # Contar registros en tablas principales
        print(f"\n📊 CONTEO DE REGISTROS:")
        for tabla in ['users', 'facturas', 'historico_consumo']:
            if tabla in tablas_restantes:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                print(f"  {tabla}: {count} registros")
        
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
    finally:
        conn.close()

def main():
    print("🚀 SCRIPT PARA REVERTIR TABLAS AGREGADAS")
    print("Este script eliminará las siguientes tablas:")
    print("- notificaciones")
    print("- procesamiento_facturas") 
    print("- sincronizaciones")
    print("- user_nics")
    print("Y la columna 'fcm_token' de la tabla 'users'")
    print()
    
    # Hacer backup
    backup_file = hacer_backup()
    
    if backup_file:
        print(f"💾 Backup guardado como: {backup_file}")
        print("   Puedes restaurar desde este backup si algo sale mal")
        print()
    
    # Confirmar antes de proceder
    respuesta = input("¿Continuar con la eliminación? (s/N): ").lower().strip()
    
    if respuesta == 's' or respuesta == 'si' or respuesta == 'sí':
        # Eliminar tablas
        if eliminar_tablas_agregadas():
            # Verificar resultado
            verificar_estructura_final()
            
            print(f"\n✅ PROCESO COMPLETADO EXITOSAMENTE!")
            print(f"🗂️  La base de datos ha sido revertida al estado anterior")
            if backup_file:
                print(f"💾 Backup disponible en: {backup_file}")
        else:
            print(f"\n❌ PROCESO FALLÓ!")
            if backup_file:
                print(f"💾 Puedes restaurar desde: {backup_file}")
                print(f"   Comando: cp {backup_file} consumo.db")
    else:
        print("❌ Operación cancelada por el usuario")
        if backup_file:
            # Eliminar backup si no se usó
            os.remove(backup_file)
            print("🗑️  Backup eliminado (no se usó)")

if __name__ == "__main__":
    main()
