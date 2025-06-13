from fastapi import FastAPI
from app.api import factura_api, auth_api, historico_api, anomalias_api

app = FastAPI(title="E-Consumo API")

# Incluir rutas
app.include_router(factura_api.router, prefix="/facturas", tags=["Facturas"])
app.include_router(auth_api.router, prefix="/auth", tags=["Autenticacion"])
app.include_router(historico_api.router, prefix="/historico", tags=["Historico"])
app.include_router(anomalias_api.router, prefix="/anomalias", tags=["Anomalias"])

