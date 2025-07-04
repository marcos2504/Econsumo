#!/usr/bin/env python3
"""
Migración para agregar la columna gmail_refresh_token a la tabla users
"""
import sqlite3
import os

def migrate_refresh_token():
    """Agregar columna gmail_refresh_token a la tabla users"""
    
    db_path = 'consumo.db'
    
    if not os.path.exists(db_path):
        print(f"❌ No se encontró la base de datos: {db_path}")
        return False
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la columna ya existe
        cursor.execute('PRAGMA table_info(users);')
        columns = [row[1] for row in cursor.fetchall()]
        
        print("📋 Columnas actuales en la tabla users:")
        for col in columns:
            print(f"  - {col}")
        
        if 'gmail_refresh_token' not in columns:
            print('\n📦 Agregando columna gmail_refresh_token...')
            cursor.execute('ALTER TABLE users ADD COLUMN gmail_refresh_token TEXT;')
            conn.commit()
            print('✅ Columna gmail_refresh_token agregada exitosamente')
        else:
            print('\n✅ La columna gmail_refresh_token ya existe')
        
        # Verificar el resultado final
        cursor.execute('PRAGMA table_info(users);')
        columns_after = cursor.fetchall()
        print('\n📋 Estructura final de la tabla users:')
        for col in columns_after:
            print(f"  - {col[1]}: {col[2]} {'(NUEVA)' if col[1] == 'gmail_refresh_token' else ''}")
        
        # Verificar usuarios existentes
        cursor.execute('SELECT id, email, gmail_token IS NOT NULL as has_token, gmail_refresh_token IS NOT NULL as has_refresh FROM users;')
        users = cursor.fetchall()
        
        print(f'\n👥 Estado de tokens de {len(users)} usuarios:')
        for user in users:
            token_status = "✅" if user[2] else "❌"
            refresh_status = "✅" if user[3] else "❌"
            print(f"  - ID {user[0]} ({user[1]}): Gmail Token: {token_status}, Refresh Token: {refresh_status}")
        
        return True
        
    except Exception as e:
        print(f'❌ Error durante la migración: {e}')
        if 'conn' in locals():
            conn.rollback()
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🔧 MIGRACIÓN: Agregando soporte para Gmail Refresh Token")
    print("=" * 60)
    
    success = migrate_refresh_token()
    
    if success:
        print("\n🎉 Migración completada exitosamente!")
        print("\n📝 PRÓXIMOS PASOS:")
        print("1. Actualizar tu frontend para enviar refresh_token durante la autenticación")
        print("2. El refresh_token es CRÍTICO para el sistema de notificaciones")
        print("3. Reiniciar el servidor para usar el nuevo modelo")
    else:
        print("\n❌ La migración falló. Revisa los errores arriba.")
