import os
import requests
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.services.auth import get_current_user, verify_google_token, logger
from app.services.jwt_service import create_access_token
from app.db.session import get_db
from app.models.user_model import User
from app.schemas.user_schemas import UserResponse, TokenResponse
from app.crud.user_crud import get_or_create_user, get_user_by_email

router = APIRouter()

@router.get("/health")
def health_check():
    """Endpoint simple de salud de la API"""
    return {
        "status": "ok",
        "message": "API funcionando correctamente",
        "timestamp": "2025-06-13"
    }

@router.post("/android", response_model=TokenResponse)
def autenticar_android(
    email: str = Query(..., description="Email del usuario autenticado con Google"),
    id_token: str = Query(..., description="ID Token de Google desde Android"),
    server_auth_code: str = Query(None, description="Server Auth Code de Google desde Android"),
    db: Session = Depends(get_db)
):
    """
    🤖 Endpoint ÚNICO para autenticación desde Android
    
    Flujo completo:
    1. Autentica al usuario con el ID Token
    2. Intercambia el Server Auth Code por Access Token de Gmail
    3. Guarda ambos tokens en la base de datos
    4. Retorna JWT para la sesión
    """
    try:
        logger.info(f"🤖 Iniciando autenticación Android para: {email}")
        
        # 1. Verificar y autenticar con ID Token
        token_data = verify_google_token(id_token)
        
        # Verificar que el email coincida
        if token_data.get("email") != email:
            logger.warning(f"Email no coincide: esperado {email}, recibido {token_data.get('email')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El email no coincide con el token de Google"
            )
        
        # Extraer información del usuario
        google_id = token_data.get("sub")
        name = token_data.get("name")
        picture = token_data.get("picture")
        
        if not google_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de Google no contiene información suficiente"
            )
        
        # 2. Intercambiar Server Auth Code por Gmail Access Token
        gmail_access_token = None
        if server_auth_code:
            try:
                gmail_access_token = exchange_server_auth_code_for_gmail_token(server_auth_code)
                logger.info(f"✅ Access token de Gmail obtenido para: {email}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo obtener access token de Gmail: {e}")
                # No fallar si no se puede obtener el token de Gmail
        
        # 3. Crear o actualizar usuario con toda la información
        user = get_or_create_user(
            db=db,
            email=email,
            google_id=google_id,
            name=name,
            picture=picture,
            gmail_token=gmail_access_token
        )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario inactivo"
            )
        
        # 4. Generar JWT para la sesión
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id}
        )
        
        logger.info(f"✅ Autenticación Android exitosa para: {user.email}")
        if gmail_access_token:
            logger.info(f"🔐 Token de Gmail guardado correctamente")
        
        return TokenResponse(token=access_token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en autenticación Android: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

def exchange_server_auth_code_for_gmail_token(server_auth_code: str) -> str:
    """
    Intercambia el Server Auth Code por un Access Token de Gmail
    """
    try:
        # Configuración OAuth2 desde variables de entorno
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            raise ValueError("GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET deben estar configurados en .env")
        
        # Intercambiar el código por tokens
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': server_auth_code,
            'grant_type': 'authorization_code',
            'access_type': 'offline'
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            if access_token:
                logger.info("🔄 Access token intercambiado exitosamente")
                return access_token
            else:
                raise ValueError("No se recibió access_token en la respuesta de Google")
        else:
            logger.error(f"Error en intercambio de token: {response.status_code} - {response.text}")
            raise ValueError(f"Error al intercambiar token con Google: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error al intercambiar server auth code: {e}")
        raise e

@router.post("/update-gmail-token")
def actualizar_gmail_token(
    gmail_token: str = Query(..., description="Nuevo Access Token de Gmail"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🔄 Actualizar solo el token de Gmail del usuario autenticado
    """
    try:
        current_user.gmail_token = gmail_token
        db.commit()
        
        logger.info(f"🔐 Token de Gmail actualizado para: {current_user.email}")
        
        return {
            "message": "Token de Gmail actualizado correctamente",
            "user_email": current_user.email,
            "has_gmail_token": True
        }
        
    except Exception as e:
        logger.error(f"❌ Error al actualizar token de Gmail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar token de Gmail: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
def obtener_usuario_actual(current_user: User = Depends(get_current_user)):
    """👤 Obtener información del usuario autenticado"""
    return current_user

@router.get("/validate")
def validar_sesion(current_user: User = Depends(get_current_user)):
    """✅ Validar que el JWT sea válido y obtener información básica"""
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "has_gmail_token": bool(current_user.gmail_token)
    }