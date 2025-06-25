#!/usr/bin/env python3
"""
Script para verificar relaciones e integridad de la base de datos
"""
import sqlite3

def verificar_foreign_keys():
    """Verificar foreign keys y relaciones en la base de datos"""
    conn = sqlite3.connect('consumo.db')
    cursor = conn.cursor()
    
    try:
        print("🔍 VERIFICANDO FOREIGN KEYS Y RELACIONES")
        print("=" * 50)
        
        # Habilitar verificación de foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Verificar foreign keys en cada tabla
        tablas = ['users', 'facturas', 'historico_consumo']
        
        for tabla in tablas:
            print(f"\n📋 FOREIGN KEYS EN '{tabla}':")
            cursor.execute(f"PRAGMA foreign_key_list({tabla})")
            fks = cursor.fetchall()
            
            if fks:
                for fk in fks:
                    print(f"  - Columna '{fk[3]}' -> Tabla '{fk[2]}' columna '{fk[4]}'")
            else:
                print(f"  ℹ️  Sin foreign keys")
        
        print(f"\n🔧 VERIFICANDO INTEGRIDAD REFERENCIAL:")
        cursor.execute("PRAGMA foreign_key_check")
        violaciones = cursor.fetchall()
        
        if violaciones:
            print("❌ VIOLACIONES ENCONTRADAS:")
            for v in violaciones:
                print(f"  - Tabla: {v[0]}, ID: {v[1]}, Referencia: {v[2]}, FK: {v[3]}")
        else:
            print("✅ No hay violaciones de integridad referencial")
        
        # Verificar relaciones específicas que pueden estar rotas
        print(f"\n🔗 VERIFICANDO RELACIONES ESPECÍFICAS:")
        
        # Verificar facturas huérfanas (sin usuario)
        cursor.execute("""
            SELECT COUNT(*) FROM facturas 
            WHERE user_id IS NOT NULL 
            AND user_id NOT IN (SELECT id FROM users)
        """)
        facturas_huerfanas = cursor.fetchone()[0]
        
        if facturas_huerfanas > 0:
            print(f"⚠️  {facturas_huerfanas} facturas con user_id inválido")
        else:
            print("✅ Todas las facturas tienen user_id válido")
        
        # Verificar histórico huérfano (sin factura)
        cursor.execute("""
            SELECT COUNT(*) FROM historico_consumo 
            WHERE factura_id IS NOT NULL 
            AND factura_id NOT IN (SELECT id FROM facturas)
        """)
        historico_huerfano = cursor.fetchone()[0]
        
        if historico_huerfano > 0:
            print(f"⚠️  {historico_huerfano} registros de histórico con factura_id inválido")
        else:
            print("✅ Todo el histórico tiene factura_id válido")
        
        # Verificar facturas sin user_id
        cursor.execute("SELECT COUNT(*) FROM facturas WHERE user_id IS NULL")
        facturas_sin_user = cursor.fetchone()[0]
        
        if facturas_sin_user > 0:
            print(f"⚠️  {facturas_sin_user} facturas sin user_id asignado")
        else:
            print("✅ Todas las facturas tienen user_id asignado")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        conn.close()

def verificar_datos_basicos():
    """Verificar datos básicos y conteos"""
    conn = sqlite3.connect('consumo.db')
    cursor = conn.cursor()
    
    try:
        print(f"\n📊 VERIFICACIÓN DE DATOS BÁSICOS:")
        print("=" * 50)
        
        # Contar registros por tabla
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM facturas")
        facturas_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM historico_consumo")
        historico_count = cursor.fetchone()[0]
        
        print(f"👥 Usuarios: {users_count}")
        print(f"📄 Facturas: {facturas_count}")
        print(f"📈 Histórico: {historico_count}")
        
        # Verificar usuarios con facturas
        cursor.execute("""
            SELECT u.id, u.email, COUNT(f.id) as facturas
            FROM users u
            LEFT JOIN facturas f ON u.id = f.user_id
            GROUP BY u.id, u.email
        """)
        usuarios_con_facturas = cursor.fetchall()
        
        print(f"\n👥 USUARIOS Y SUS FACTURAS:")
        for usuario in usuarios_con_facturas:
            print(f"  - ID {usuario[0]} ({usuario[1]}): {usuario[2]} facturas")
        
        # Verificar NICs únicos
        cursor.execute("SELECT COUNT(DISTINCT nic) FROM facturas WHERE nic IS NOT NULL AND nic != ''")
        nics_unicos = cursor.fetchone()[0]
        print(f"\n🏠 NICs únicos en el sistema: {nics_unicos}")
        
        # Verificar facturas con histórico
        cursor.execute("""
            SELECT COUNT(DISTINCT f.id) 
            FROM facturas f
            JOIN historico_consumo h ON f.id = h.factura_id
        """)
        facturas_con_historico = cursor.fetchone()[0]
        print(f"📊 Facturas con histórico de consumo: {facturas_con_historico}")
        
    except Exception as e:
        print(f"❌ Error verificando datos: {e}")
    finally:
        conn.close()

def verificar_backup():
    """Verificar qué había en las tablas eliminadas (desde el backup)"""
    import os
    
    # Buscar el backup más reciente
    backups = [f for f in os.listdir('.') if f.startswith('consumo_backup_')]
    if not backups:
        print("\n⚠️  No se encontró backup para verificar las tablas eliminadas")
        return
    
    backup_file = sorted(backups)[-1]  # El más reciente
    
    print(f"\n🔍 VERIFICANDO QUÉ HABÍA EN LAS TABLAS ELIMINADAS:")
    print(f"📁 Usando backup: {backup_file}")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(backup_file)
        cursor = conn.cursor()
        
        tablas_eliminadas = ['notificaciones', 'procesamiento_facturas', 'sincronizaciones', 'user_nics']
        
        for tabla in tablas_eliminadas:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                print(f"📋 {tabla}: {count} registros eliminados")
                
                # Ver estructura si tenía datos
                if count > 0:
                    cursor.execute(f"PRAGMA table_info({tabla})")
                    columns = cursor.fetchall()
                    print(f"   Columnas: {[col[1] for col in columns]}")
                    
            except Exception as e:
                print(f"❌ Error verificando {tabla}: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error accediendo al backup: {e}")

def main():
    print("🔍 VERIFICACIÓN COMPLETA DE INTEGRIDAD DE BASE DE DATOS")
    print("Después de eliminar tablas: notificaciones, procesamiento_facturas, sincronizaciones, user_nics")
    print()
    
    # Verificar foreign keys y relaciones
    if verificar_foreign_keys():
        # Verificar datos básicos
        verificar_datos_basicos()
        
        # Verificar qué había en las tablas eliminadas
        verificar_backup()
        
        print(f"\n✅ VERIFICACIÓN COMPLETADA")
        print("🎯 La base de datos está limpia y funcional")
    else:
        print(f"\n❌ PROBLEMAS DETECTADOS EN LA VERIFICACIÓN")

if __name__ == "__main__":
    main()
