import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session
from app.models.historico_model import HistoricoConsumo
from app.models.factura_model import Factura
import numpy as np

def detectar_anomalias_por_nic(db: Session, nic: str, user_id: int):
    # Buscar históricos a través de la relación con facturas filtrado por usuario
    query = db.query(HistoricoConsumo)\
              .join(Factura, HistoricoConsumo.factura_id == Factura.id)\
              .filter(Factura.nic == nic, Factura.user_id == user_id)
    
    df = pd.read_sql(query.statement, db.bind)

    if df.empty:
        return []

    # Convertir fechas a datetime
    try:
        df["fecha"] = pd.to_datetime(df["fecha"], format="%m/%y")
    except:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"])
    df["trimestre"] = df["fecha"].dt.to_period("Q")
    df["año"] = df["fecha"].dt.year

    resultados = []

    for trimestre, grupo in df.groupby("trimestre"):
        if len(grupo) < 1:
            continue

        num_trim = trimestre.quarter
        año_actual = grupo["año"].iloc[0]
        historico = df[(df["fecha"].dt.quarter == num_trim) & (df["año"] < año_actual)]

        if len(historico) < 1:
            # Si no hay datos históricos, usar todo el historial disponible
            historico = df[df["año"] < año_actual]
            if len(historico) < 1:
                continue

        X_train = historico[["consumo_kwh"]]
        X_test = grupo[["consumo_kwh"]]

        # 🔧 MEJORAS EN EL MODELO DE DETECCIÓN
        
        # 1. Calcular estadísticas del histórico
        promedio_historico = X_train["consumo_kwh"].mean()
        std_historico = X_train["consumo_kwh"].std()
        q75 = X_train["consumo_kwh"].quantile(0.75)
        q25 = X_train["consumo_kwh"].quantile(0.25)
        iqr = q75 - q25
        
        # 2. Usar modelo de Isolation Forest con configuración mejorada
        # Contamination más agresiva para detectar extremos
        contamination_rate = min(0.3, max(0.05, 1.0 / len(X_train))) if len(X_train) > 3 else 0.5
        modelo = IsolationForest(contamination=contamination_rate, random_state=42, n_estimators=200)
        modelo.fit(X_train)

        grupo = grupo.copy()
        
        # 3. Predicción del modelo
        prediccion_modelo = modelo.predict(X_test)
        scores_modelo = modelo.decision_function(X_test)
        
        # 4. REGLAS ADICIONALES PARA DETECCIÓN EXTREMA
        # Detectar anomalías por desviación extrema (>300% o <-70%)
        variaciones = ((grupo["consumo_kwh"] - promedio_historico) / promedio_historico * 100)
        
        anomalias_finales = []
        for i, (score, variacion, consumo) in enumerate(zip(scores_modelo, variaciones, grupo["consumo_kwh"])):
            # Regla 1: Modelo detecta anomalía
            anomalia_modelo = prediccion_modelo[i] == -1
            
            # Regla 2: Variación extrema (>200% o <-60%)
            anomalia_extrema = abs(variacion) > 200
            
            # Regla 3: Fuera del rango IQR extremo (>3*IQR del Q75)
            anomalia_iqr = consumo > (q75 + 3 * iqr) or consumo < (q25 - 3 * iqr)
            
            # Regla 4: Más de 4 desviaciones estándar
            anomalia_std = abs(consumo - promedio_historico) > (4 * std_historico)
            
            # DECISIÓN FINAL: Es anomalía si cumple cualquiera de las reglas
            es_anomalia = anomalia_modelo or anomalia_extrema or anomalia_iqr or anomalia_std
            
            anomalias_finales.append(-1 if es_anomalia else 1)
        
        grupo["anomalia"] = anomalias_finales
        grupo["score"] = scores_modelo
        grupo["trimestre"] = grupo["trimestre"].astype(str)
        
        # 5. Calcular comparación con promedio histórico
        grupo["comparado_trimestre"] = ((grupo["consumo_kwh"] - promedio_historico) / promedio_historico * 100).round(1)
        
        # 6. Agregar información de debugging
        grupo["promedio_historico"] = promedio_historico
        grupo["std_historico"] = std_historico
        grupo["variacion_abs"] = abs(grupo["comparado_trimestre"])

        resultados.append(grupo)

       
    if resultados:
        return pd.concat(resultados).to_dict(orient="records")
    return []

def alerta_anomalia_actual(db: Session, nic: str, user_id: int):
    anomalias = detectar_anomalias_por_nic(db, nic, user_id)
    if not anomalias:
        return {"estado": "sin_datos"}
    anomalias.sort(key=lambda x: pd.to_datetime(x["fecha"]))
    mas_reciente = anomalias[-1]
    return {
        "fecha": mas_reciente["fecha"],
        "consumo_kwh": mas_reciente["consumo_kwh"],
        "anomalia": mas_reciente["anomalia"] == -1,
        "score": mas_reciente["score"],
        "comparado_trimestre": mas_reciente.get("comparado_trimestre")
    }
