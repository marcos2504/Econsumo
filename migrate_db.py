"""
Script de migración para asociar facturas existentes con usuarios
"""
import sqlite3
from datetime import datetime

def migrate_database():
    conn = sqlite3.connect('consumo.db')
    cursor = conn.cursor()
    
    try:
        # Verificar si ya existe la columna user_id en facturas
        cursor.execute("PRAGMA table_info(facturas)")
        factura_columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in factura_columns:
            print("🔄 Agregando columna user_id a facturas...")
            
            # Verificar si hay usuarios en la tabla users
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            if user_count == 0:
                # Crear usuario por defecto si no hay usuarios
                cursor.execute('''
                    INSERT INTO users (email, full_name, google_id, is_active, created_at, updated_at)
                    VALUES ('usuario@ejemplo.com', 'Usuario por defecto', 'default_user', 1, ?, ?)
                ''', (datetime.now(), datetime.now()))
                print("✅ Usuario por defecto creado")
            
            # Agregar columna user_id a facturas
            cursor.execute('ALTER TABLE facturas ADD COLUMN user_id INTEGER')
            
            # Asignar todas las facturas existentes al primer usuario
            cursor.execute('SELECT id FROM users LIMIT 1')
            first_user_id = cursor.fetchone()[0]
            
            cursor.execute('UPDATE facturas SET user_id = ? WHERE user_id IS NULL', (first_user_id,))
            
            print(f"✅ Columna user_id agregada a facturas y facturas asociadas al usuario ID {first_user_id}")
        else:
            print("✅ La tabla facturas ya tiene la columna user_id")
        
        # Verificar que el modelo User tenga un campo 'name' para compatibilidad
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [column[1] for column in cursor.fetchall()]
        
        if 'name' not in user_columns and 'full_name' in user_columns:
            print("ℹ️  La tabla users usa 'full_name' en lugar de 'name' - esto es compatible")
        
        conn.commit()
        print("✅ Migración completada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()