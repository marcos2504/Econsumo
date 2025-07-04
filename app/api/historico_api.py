from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.historico_model import HistoricoConsumo
from app.models.factura_model import Factura
from app.services.auth import get_current_user
from app.models.user_model import User
from typing import Optional

router = APIRouter()

@router.get("/")
def listar_todo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Filtrar histórico por usuario a través de las facturas
    return db.query(HistoricoConsumo)\
             .join(Factura, HistoricoConsumo.factura_id == Factura.id)\
             .filter(Factura.user_id == current_user.id)\
             .all()

# ENDPOINT TEMPORAL SIN JWT - HISTÓRICO POR NIC
@router.get("/nic/{nic}")
def listar_por_nic_sin_jwt(
    nic: str,
    user_id: Optional[int] = Query(default=2, description="ID del usuario (temporal)"),
    db: Session = Depends(get_db)
):
    """
    ENDPOINT TEMPORAL SIN JWT - Solo para pruebas
    Obtener histórico de consumo por NIC
    
    Args:
        nic: Número de NIC a consultar
        user_id: ID del usuario (default=2)
    
    Returns:
        Array con histórico de consumo del NIC
    """
    try:
        # Verificar que el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {
                "error": f"Usuario con ID {user_id} no encontrado",
                "nic": nic,
                "historico": []
            }
        
        # Buscar históricos por NIC y usuario
        historico = db.query(HistoricoConsumo)\
                     .join(Factura, HistoricoConsumo.factura_id == Factura.id)\
                     .filter(Factura.nic == nic, Factura.user_id == user_id)\
                     .order_by(HistoricoConsumo.fecha)\
                     .all()
        
        # Formatear respuesta
        historico_formateado = []
        for registro in historico:
            historico_formateado.append({
                "id": registro.id,
                "fecha": registro.fecha,
                "consumo_kwh": registro.consumo_kwh,
                "factura_id": registro.factura_id
            })
        
        return {
            "nic": nic,
            "total_registros": len(historico_formateado),
            "historico": historico_formateado,
            "usuario": {
                "id": user.id,
                "email": user.email
            },
            "modo": "SIN_JWT_TEMPORAL"
        }
        
    except Exception as e:
        return {
            "error": f"Error obteniendo histórico: {str(e)}",
            "nic": nic,
            "historico": [],
            "user_id": user_id
        }

# ENDPOINT ORIGINAL CON JWT (para producción)
@router.get("/nic_con_jwt/{nic}")
def listar_por_nic_con_jwt(
    nic: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint original con JWT para producción
    """
    # Buscar históricos por NIC y usuario
    return db.query(HistoricoConsumo)\
             .join(Factura, HistoricoConsumo.factura_id == Factura.id)\
             .filter(Factura.nic == nic, Factura.user_id == current_user.id)\
             .all()

@router.get("/factura/{factura_id}")
def listar_por_factura(
    factura_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar que la factura pertenece al usuario
    factura = db.query(Factura).filter(
        Factura.id == factura_id, 
        Factura.user_id == current_user.id
    ).first()
    
    if not factura:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    return db.query(HistoricoConsumo).filter(HistoricoConsumo.factura_id == factura_id).all()

# ENDPOINTS MEJORADOS CON JWT PARA FRONTEND
@router.get("/ver_historico/{nic}")
def ver_historico_completo(
    nic: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🎯 ENDPOINT PRINCIPAL PARA VER HISTÓRICO EN FRONTEND
    Obtener histórico completo optimizado para gráficos
    
    Args:
        nic: Número de NIC a consultar
    
    Returns:
        Datos completos del histórico con estadísticas para gráficos
    """
    try:
        # Buscar históricos por NIC y usuario ordenados por fecha
        historico = db.query(HistoricoConsumo)\
                     .join(Factura, HistoricoConsumo.factura_id == Factura.id)\
                     .filter(Factura.nic == nic, Factura.user_id == current_user.id)\
                     .order_by(HistoricoConsumo.fecha)\
                     .all()
        
        if not historico:
            return {
                "nic": nic,
                "usuario": current_user.email,
                "error": "No se encontró histórico para este NIC",
                "datos": [],
                "estadisticas": None,
                "para_grafico": []
            }
        
        # Formatear datos para el frontend
        datos_formateados = []
        consumos = []
        
        for registro in historico:
            # Obtener dirección de la factura
            factura = db.query(Factura).filter(Factura.id == registro.factura_id).first()
            direccion = factura.direccion if factura else "N/A"
            
            dato = {
                "id": registro.id,
                "fecha": registro.fecha,
                "consumo_kwh": float(registro.consumo_kwh) if registro.consumo_kwh else 0,
                "nic": nic,
                "direccion": direccion,
                "factura_id": registro.factura_id
            }
            datos_formateados.append(dato)
            consumos.append(dato["consumo_kwh"])
        
        # Calcular estadísticas
        if consumos:
            promedio = sum(consumos) / len(consumos)
            maximo = max(consumos)
            minimo = min(consumos)
            total_consumo = sum(consumos)
        else:
            promedio = maximo = minimo = total_consumo = 0
        
        # Datos optimizados para gráficos
        para_grafico = [
            {"fecha": d["fecha"], "consumo": d["consumo_kwh"]}
            for d in datos_formateados
        ]
        
        return {
            "nic": nic,
            "usuario": current_user.email,
            "total_registros": len(datos_formateados),
            "datos": datos_formateados,
            "para_grafico": para_grafico,
            "estadisticas": {
                "promedio": round(promedio, 2),
                "maximo": round(maximo, 2),
                "minimo": round(minimo, 2),
                "total_consumo": round(total_consumo, 2)
            }
        }
        
    except Exception as e:
        return {
            "error": f"Error obteniendo histórico completo: {str(e)}",
            "nic": nic,
            "usuario": current_user.email,
            "datos": []
        }

@router.get("/resumen_rapido/{nic}")
def resumen_historico_rapido(
    nic: str,
    meses: Optional[int] = Query(default=6, description="Número de meses recientes (default: 6)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 RESUMEN RÁPIDO DEL HISTÓRICO
    Para mostrar en cards o widgets pequeños
    
    Args:
        nic: Número de NIC
        meses: Cantidad de meses recientes a mostrar
    """
    try:
        # Obtener histórico limitado a X meses más recientes
        historico = db.query(HistoricoConsumo)\
                     .join(Factura, HistoricoConsumo.factura_id == Factura.id)\
                     .filter(Factura.nic == nic, Factura.user_id == current_user.id)\
                     .order_by(HistoricoConsumo.fecha.desc())\
                     .limit(meses)\
                     .all()
        
        if not historico:
            return {
                "nic": nic,
                "estado": "sin_datos",
                "ultimo_consumo": None,
                "promedio_reciente": None,
                "datos_recientes": []
            }
        
        # Extraer consumos
        consumos = [float(h.consumo_kwh) if h.consumo_kwh else 0 for h in historico]
        
        # Calcular estadísticas rápidas
        ultimo = consumos[0] if consumos else 0  # El más reciente (orden DESC)
        promedio = sum(consumos) / len(consumos) if consumos else 0
        
        # Datos recientes en formato simple
        datos_recientes = [
            {
                "fecha": h.fecha,
                "consumo": float(h.consumo_kwh) if h.consumo_kwh else 0
            }
            for h in reversed(historico)  # Revertir para orden cronológico
        ]
        
        return {
            "nic": nic,
            "estado": "ok",
            "ultimo_consumo": round(ultimo, 2),
            "fecha_ultimo": historico[0].fecha if historico else None,
            "promedio_reciente": round(promedio, 2),
            "total_meses": len(historico),
            "datos_recientes": datos_recientes
        }
        
    except Exception as e:
        return {
            "error": f"Error en resumen rápido: {str(e)}",
            "nic": nic,
            "estado": "error"
        }

# ENDPOINTS CON FILTROS AVANZADOS
@router.get("/filtrado/{nic}")
def historico_filtrado(
    nic: str,
    fecha_desde: Optional[str] = Query(None, description="Fecha desde formato MM/YY (ej: 01/24)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta formato MM/YY (ej: 12/24)"),
    ultimos_meses: Optional[int] = Query(None, description="Últimos X meses (alternativa a fechas)"),
    ordenar_por: Optional[str] = Query("fecha", description="Ordenar por: fecha, consumo"),
    orden: Optional[str] = Query("asc", description="Orden: asc, desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📅 HISTÓRICO CON FILTROS AVANZADOS
    Filtrar por fechas, períodos, ordenamiento
    
    Args:
        nic: Número de NIC
        fecha_desde: Fecha desde (MM/YY)
        fecha_hasta: Fecha hasta (MM/YY)
        ultimos_meses: Alternativamente, últimos X meses
        ordenar_por: Campo para ordenar (fecha, consumo)
        orden: Dirección del orden (asc, desc)
    
    Examples:
        /historico/filtrado/3005000?fecha_desde=01/24&fecha_hasta=06/24
        /historico/filtrado/3005000?ultimos_meses=6
        /historico/filtrado/3005000?ordenar_por=consumo&orden=desc
    """
    try:
        # Query base
        query = db.query(HistoricoConsumo)\
                  .join(Factura, HistoricoConsumo.factura_id == Factura.id)\
                  .filter(Factura.nic == nic, Factura.user_id == current_user.id)
        
        # Aplicar filtros de fecha
        if fecha_desde or fecha_hasta:
            if fecha_desde:
                query = query.filter(HistoricoConsumo.fecha >= fecha_desde)
            if fecha_hasta:
                query = query.filter(HistoricoConsumo.fecha <= fecha_hasta)
        elif ultimos_meses:
            # Si especifica últimos X meses, obtener los más recientes
            query = query.order_by(HistoricoConsumo.fecha.desc()).limit(ultimos_meses)
        
        # Aplicar ordenamiento
        if ordenar_por == "consumo":
            if orden == "desc":
                query = query.order_by(HistoricoConsumo.consumo_kwh.desc())
            else:
                query = query.order_by(HistoricoConsumo.consumo_kwh.asc())
        else:  # ordenar por fecha (default)
            if orden == "desc":
                query = query.order_by(HistoricoConsumo.fecha.desc())
            else:
                query = query.order_by(HistoricoConsumo.fecha.asc())
        
        # Ejecutar query
        historico = query.all()
        
        if not historico:
            return {
                "nic": nic,
                "usuario": current_user.email,
                "filtros_aplicados": {
                    "fecha_desde": fecha_desde,
                    "fecha_hasta": fecha_hasta,
                    "ultimos_meses": ultimos_meses,
                    "ordenar_por": ordenar_por,
                    "orden": orden
                },
                "mensaje": "No se encontraron datos con los filtros aplicados",
                "datos": [],
                "estadisticas": None
            }
        
        # Formatear datos
        datos_formateados = []
        consumos = []
        
        for registro in historico:
            dato = {
                "id": registro.id,
                "fecha": registro.fecha,
                "consumo_kwh": float(registro.consumo_kwh) if registro.consumo_kwh else 0,
                "factura_id": registro.factura_id
            }
            datos_formateados.append(dato)
            consumos.append(dato["consumo_kwh"])
        
        # Calcular estadísticas del período filtrado
        if consumos:
            promedio = sum(consumos) / len(consumos)
            maximo = max(consumos)
            minimo = min(consumos)
            total_consumo = sum(consumos)
        else:
            promedio = maximo = minimo = total_consumo = 0
        
        return {
            "nic": nic,
            "usuario": current_user.email,
            "filtros_aplicados": {
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "ultimos_meses": ultimos_meses,
                "ordenar_por": ordenar_por,
                "orden": orden
            },
            "total_registros": len(datos_formateados),
            "datos": datos_formateados,
            "estadisticas": {
                "promedio": round(promedio, 2),
                "maximo": round(maximo, 2),
                "minimo": round(minimo, 2),
                "total_consumo": round(total_consumo, 2),
                "periodo_meses": len(consumos)
            }
        }
        
    except Exception as e:
        return {
            "error": f"Error en histórico filtrado: {str(e)}",
            "nic": nic,
            "usuario": current_user.email,
            "datos": []
        }

@router.get("/por_periodo/{nic}")
def historico_por_periodo(
    nic: str,
    periodo: str = Query(..., description="Período: ultimo_mes, ultimos_3_meses, ultimos_6_meses, ultimo_año, todo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 HISTÓRICO POR PERÍODOS PREDEFINIDOS
    Filtros rápidos para períodos comunes
    
    Args:
        nic: Número de NIC
        periodo: Período predefinido
    
    Examples:
        /historico/por_periodo/3005000?periodo=ultimos_3_meses
        /historico/por_periodo/3005000?periodo=ultimo_año
    """
    try:
        # Definir límites según período
        limite_registros = {
            "ultimo_mes": 1,
            "ultimos_3_meses": 3,
            "ultimos_6_meses": 6,
            "ultimo_año": 12,
            "todo": None
        }
        
        if periodo not in limite_registros:
            return {
                "error": f"Período '{periodo}' no válido",
                "periodos_validos": list(limite_registros.keys()),
                "nic": nic
            }
        
        # Query base
        query = db.query(HistoricoConsumo)\
                  .join(Factura, HistoricoConsumo.factura_id == Factura.id)\
                  .filter(Factura.nic == nic, Factura.user_id == current_user.id)\
                  .order_by(HistoricoConsumo.fecha.desc())
        
        # Aplicar límite si no es "todo"
        limite = limite_registros[periodo]
        if limite:
            query = query.limit(limite)
        
        historico = query.all()
        
        # Revertir orden para cronológico
        historico = list(reversed(historico))
        
        if not historico:
            return {
                "nic": nic,
                "usuario": current_user.email,
                "periodo": periodo,
                "mensaje": "No hay datos para este período",
                "datos": [],
                "para_grafico": []
            }
        
        # Formatear datos
        datos = [
            {
                "fecha": h.fecha,
                "consumo_kwh": float(h.consumo_kwh) if h.consumo_kwh else 0,
                "factura_id": h.factura_id
            }
            for h in historico
        ]
        
        # Datos para gráfico
        para_grafico = [
            {
                "fecha": h.fecha,
                "consumo": float(h.consumo_kwh) if h.consumo_kwh else 0
            }
            for h in historico
        ]
        
        # Estadísticas
        consumos = [d["consumo_kwh"] for d in datos]
        if consumos:
            estadisticas = {
                "promedio": round(sum(consumos) / len(consumos), 2),
                "maximo": round(max(consumos), 2),
                "minimo": round(min(consumos), 2),
                "total": round(sum(consumos), 2)
            }
        else:
            estadisticas = {"promedio": 0, "maximo": 0, "minimo": 0, "total": 0}
        
        return {
            "nic": nic,
            "usuario": current_user.email,
            "periodo": periodo,
            "total_registros": len(datos),
            "datos": datos,
            "para_grafico": para_grafico,
            "estadisticas": estadisticas
        }
        
    except Exception as e:
        return {
            "error": f"Error en período {periodo}: {str(e)}",
            "nic": nic,
            "usuario": current_user.email,
            "datos": []
        }

# ENDPOINT PARA AGREGAR HISTÓRICO MANUALMENTE CON VALIDACIÓN
@router.post("/agregar_registro")
def agregar_registro_historico(
    nic: str,
    fecha: str,
    consumo_kwh: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📝 AGREGAR REGISTRO DE HISTÓRICO MANUALMENTE
    Con validación automática de duplicados por mes/año
    
    Args:
        nic: NIC de la propiedad
        fecha: Fecha en formato MM/YYYY o DD/MM/YYYY  
        consumo_kwh: Consumo en kWh
    
    Returns:
        Resultado de la operación con validación de duplicados
    """
    try:
        # Verificar que la factura/NIC pertenece al usuario
        factura = db.query(Factura).filter(
            Factura.nic == nic,
            Factura.user_id == current_user.id
        ).first()
        
        if not factura:
            return {
                "error": f"NIC {nic} no encontrado para el usuario {current_user.email}",
                "nic": nic,
                "registro_creado": False
            }
        
        # Extraer mes y año de la fecha nueva
        clave_nueva = None
        if '/' in fecha:
            partes = fecha.split('/')
            if len(partes) >= 2:
                mes = partes[0].zfill(2) if len(partes) == 2 else partes[1].zfill(2)  # MM/YY o DD/MM/YY
                año = partes[-1]  # Último elemento (año)
                
                # Normalizar año a formato corto (24, 25, etc.) como usa el extractor
                if len(año) == 4:
                    año_corto = año[-2:]  # 2024 → 24
                else:
                    año_corto = año.zfill(2)  # 24 → 24
                
                clave_nueva = f"{mes}/{año_corto}"
        
        if not clave_nueva:
            return {
                "error": f"Formato de fecha inválido: {fecha}. Use MM/YY, MM/YYYY o DD/MM/YY",
                "nic": nic,
                "registro_creado": False
            }
        
        # Verificar duplicados existentes para este NIC/usuario
        registros_existentes = db.query(HistoricoConsumo)\
                                .join(Factura, HistoricoConsumo.factura_id == Factura.id)\
                                .filter(Factura.nic == nic, Factura.user_id == current_user.id)\
                                .all()
        
        # Buscar si ya existe un registro para el mismo mes/año
        for registro_existente in registros_existentes:
            fecha_existente = registro_existente.fecha
            if '/' in fecha_existente:
                partes_existente = fecha_existente.split('/')
                if len(partes_existente) >= 2:
                    mes_existente = partes_existente[0].zfill(2) if len(partes_existente) == 2 else partes_existente[1].zfill(2)
                    año_existente = partes_existente[-1]
                    
                    # Normalizar año a formato corto para comparación
                    if len(año_existente) == 4:
                        año_existente_corto = año_existente[-2:]  # 2024 → 24
                    else:
                        año_existente_corto = año_existente.zfill(2)  # 24 → 24
                    
                    clave_existente = f"{mes_existente}/{año_existente_corto}"
                    
                    if clave_nueva == clave_existente:
                        return {
                            "error": f"Ya existe un registro para {clave_nueva}",
                            "fecha_solicitada": fecha,
                            "fecha_existente": fecha_existente,
                            "consumo_existente": float(registro_existente.consumo_kwh),
                            "nic": nic,
                            "registro_creado": False,
                            "sugerencia": "Use el endpoint de actualización para modificar el registro existente"
                        }
        
        # Crear nuevo registro si no hay duplicados
        # IMPORTANTE: Guardar siempre en formato corto (como el extractor)
        fecha_normalizada = fecha
        if '/' in fecha:
            partes = fecha.split('/')
            if len(partes) >= 2:
                mes = partes[0].zfill(2) if len(partes) == 2 else partes[1].zfill(2)
                año = partes[-1]
                
                # Convertir a formato corto (igual que el extractor)
                if len(año) == 4:
                    año_corto = año[-2:]  # 2025 → 25
                else:
                    año_corto = año.zfill(2)  # 25 → 25
                
                fecha_normalizada = f"{mes}/{año_corto}"
        
        nuevo_registro = HistoricoConsumo(
            fecha=fecha_normalizada,  # Guardar en formato corto
            consumo_kwh=consumo_kwh,
            factura_id=factura.id
        )
        
        db.add(nuevo_registro)
        db.commit()
        db.refresh(nuevo_registro)
        
        return {
            "mensaje": f"Registro agregado exitosamente para {clave_nueva}",
            "registro": {
                "id": nuevo_registro.id,
                "fecha": nuevo_registro.fecha,  # Ya está en formato corto
                "consumo_kwh": float(nuevo_registro.consumo_kwh),
                "nic": nic,
                "factura_id": nuevo_registro.factura_id
            },
            "nic": nic,
            "usuario": current_user.email,
            "registro_creado": True,
            "validacion": f"No se encontraron duplicados para {clave_nueva}",
            "formato_usado": "corto_consistente_con_extractor"
        }
        
    except Exception as e:
        db.rollback()
        return {
            "error": f"Error agregando registro: {str(e)}",
            "nic": nic,
            "fecha": fecha,
            "registro_creado": False
        }

@router.put("/actualizar_registro/{registro_id}")
def actualizar_registro_historico(
    registro_id: int,
    consumo_kwh: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📝 ACTUALIZAR REGISTRO DE HISTÓRICO EXISTENTE
    Para modificar el consumo de un mes/año ya registrado
    """
    try:
        # Buscar el registro y verificar que pertenece al usuario
        registro = db.query(HistoricoConsumo)\
                    .join(Factura, HistoricoConsumo.factura_id == Factura.id)\
                    .filter(
                        HistoricoConsumo.id == registro_id,
                        Factura.user_id == current_user.id
                    ).first()
        
        if not registro:
            return {
                "error": f"Registro {registro_id} no encontrado o no pertenece al usuario",
                "registro_actualizado": False
            }
        
        # Guardar valores anteriores
        consumo_anterior = float(registro.consumo_kwh)
        
        # Actualizar el consumo
        registro.consumo_kwh = consumo_kwh
        db.commit()
        db.refresh(registro)
        
        return {
            "mensaje": "Registro actualizado exitosamente",
            "registro": {
                "id": registro.id,
                "fecha": registro.fecha,
                "consumo_kwh_anterior": consumo_anterior,
                "consumo_kwh_nuevo": float(registro.consumo_kwh),
                "diferencia": float(registro.consumo_kwh) - consumo_anterior
            },
            "usuario": current_user.email,
            "registro_actualizado": True
        }
        
    except Exception as e:
        db.rollback()
        return {
            "error": f"Error actualizando registro: {str(e)}",
            "registro_id": registro_id,
            "registro_actualizado": False
        }
    