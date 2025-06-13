import os
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud.user_crud import get_or_create_user, get_user_by_email
from app.models.user_model import User
from app.services.jwt_service import verify_token
from typing import Optional
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth2 scheme
security = HTTPBearer()

# Google OAuth settings
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
# Gmail API settings (para el extractor de facturas)
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_PATH = 'token.json'

def verify_google_token(token: str) -> dict:
    """Verificar token de Google OAuth"""
    try:
        logger.info(f"Verificando token de Google: {token[:20]}...")
        
        # Verificar el token con Google
        idinfo = id_token.verify_oauth2_token(
            token, requests.Request(), GOOGLE_CLIENT_ID
        )
        
        logger.info(f"Token verificado exitosamente para email: {idinfo.get('email', 'N/A')}")
        
        # Verificar que el token es válido
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
            
        return idinfo
    except ValueError as e:
        logger.error(f"Error de validación del token de Google: {str(e)}")
        # Detectar si es un authorization code en lugar de ID token
        if token.startswith('4/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El token proporcionado parece ser un código de autorización, no un ID token. "
                       "Asegúrate de enviar el ID token de Google, no el authorization code.",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token de Google inválido: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error inesperado al verificar token de Google: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error al verificar token de Google: {str(e)}",
        )

def authenticate_with_google(email: str, google_token: str, db: Session, gmail_token: str = None) -> dict:
    """Autenticar usuario con Google OAuth y retornar JWT"""
    from app.services.jwt_service import create_access_token
    
    try:
        logger.info(f"Iniciando autenticación con Google para email: {email}")
        
        # Verificar token de Google
        token_data = verify_google_token(google_token)
        
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
        
        logger.info(f"Obteniendo o creando usuario: {email}")
        
        # Obtener o crear usuario, incluyendo gmail_token si se proporciona
        user = get_or_create_user(
            db=db,
            email=email,
            google_id=google_id,
            name=name,
            picture=picture,
            gmail_token=gmail_token
        )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario inactivo"
            )
        
        # Crear JWT token
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id}
        )
        
        logger.info(f"Autenticación exitosa para usuario: {user.email}")
        if gmail_token:
            logger.info(f"Token de Gmail guardado para usuario: {user.email}")
        
        return {"token": access_token}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error interno en autenticación con Google: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

def get_current_user_from_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Obtener usuario actual desde el token JWT"""
    try:
        # Verificar token JWT
        token_data = verify_token(credentials.credentials)
        
        # Buscar usuario en la base de datos
        user = get_user_by_email(db, email=token_data["email"])
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario inactivo"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error al procesar token: {str(e)}",
        )

# Alias para compatibilidad
get_current_user = get_current_user_from_jwt

# Mantener compatibilidad con código existente


