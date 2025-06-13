"""
Servicio para manejo de base de datos
"""
import os
from app.db.session import engine, DATABASE_URL
from app.db.base import Base
from app.models import factura_model, historico_model

def init_db_if_not_exists():
    """
    Inicializar la base de datos si no existe
    """
    # Extraer el path del archivo de la URL de la base de datos
    db_path = DATABASE_URL.replace("sqlite:///", "")
    
    # Si el archivo no existe o está vacío, inicializar
    if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
        print("🔄 Base de datos no encontrada o vacía. Inicializando...")
        try:
            # Crear todas las tablas
            Base.metadata.create_all(bind=engine)
            print("✅ Base de datos inicializada correctamente")
            print("✅ Tablas creadas: facturas, historico_consumo")
            return True
        except Exception as e:
            print(f"❌ Error al inicializar la base de datos: {e}")
            return False
    else:
        print("✅ Base de datos ya existe")
        return True