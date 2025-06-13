import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session
from app.models.historico_model import HistoricoConsumo
from app.models.factura_model import Factura

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
        if len(grupo) < 0:
            continue

        num_trim = trimestre.quarter
        año_actual = grupo["año"].iloc[0]
        historico = df[(df["fecha"].dt.quarter == num_trim) & (df["año"] < año_actual)]

        if len(historico) < 1:
            continue

        X_train = historico[["consumo_kwh"]]
        X_test = grupo[["consumo_kwh"]]

        modelo = IsolationForest(contamination=0.1, random_state=42)
        modelo.fit(X_train)

        grupo = grupo.copy()
        grupo["anomalia"] = modelo.predict(X_test)
        grupo["score"] = modelo.decision_function(X_test)
        grupo["trimestre"] = grupo["trimestre"].astype(str)
        promedio_trimestre = X_train["consumo_kwh"].mean()
        grupo["comparado_trimestre"] = ((grupo["consumo_kwh"] - promedio_trimestre) / promedio_trimestre * 100).round(1)

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
