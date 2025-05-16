from fastapi import APIRouter
from app.services.auth import generar_token

router = APIRouter()

@router.post("/token")
def crear_token():
    return generar_token()