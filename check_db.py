"""
Script para revisar la estructura actual de la base de datos
"""
import sqlite3

def check_database_structure():
    conn = sqlite3.connect('consumo.db')
    cursor = conn.cursor()
    
    try:
        # Revisar todas las tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("📋 Tablas existentes:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Revisar estructura de cada tabla
        for table in tables:
            table_name = table[0]
            print(f"\n🔍 Estructura de {table_name}:")
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[1]} ({col[2]}) - PK: {col[5]}, NotNull: {col[3]}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_database_structure()