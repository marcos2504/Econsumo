from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.services.auth import get_current_user, authenticate_with_google, logger
from app.services.jwt_service import verify_token, create_access_token, create_test_token
from app.db.session import get_db
from app.models.user_model import User
from app.schemas.user_schemas import UserResponse, TokenResponse, TokenRequest

router = APIRouter()

@router.get("/health")
def health_check():
    """
    Endpoint GET /auth/health
    Endpoint simple que responde con código 200 OK
    No requiere autenticación
    """
    return {
        "status": "ok",
        "message": "API funcionando correctamente",
        "timestamp": "2025-06-13"
    }

@router.post("/token", response_model=TokenResponse)
def validar_token(token_request: TokenRequest):
    """
    Endpoint POST /auth/token
    Recibe y valida un token de autenticación existente
    Devuelve el mismo token si es válido o un error si no lo es
    """
    try:
        # Verificar que el token sea válido
        token_data = verify_token(token_request.token)
        
        # Si llegamos aquí, el token es válido
        return TokenResponse(token=token_request.token)
        
    except HTTPException as e:
        # Re-lanzar la excepción HTTP con el código de estado apropiado
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.post("/google", response_model=TokenResponse)
def autenticar_con_google(
    email: str = Query(..., description="Email del usuario autenticado con Google"),
    token: str = Query(..., description="Token de identificación de Google"),
    gmail_token: str = Query(None, description="Access Token de Google para Gmail (opcional)"),
    db: Session = Depends(get_db)
):
    """
    Endpoint POST /auth/google
    Recibe email y token de Google OAuth desde la aplicación Android
    Verifica la autenticidad del token con la API de Google
    Crea o actualiza el usuario en la base de datos
    Opcionalmente guarda el token de Gmail si se proporciona
    Genera un JWT para la sesión del usuario
    """
    try:
        # Autenticar con Google y obtener JWT
        result = authenticate_with_google(email, token, db)
        
        # Si se proporciona gmail_token, guardarlo en la base de datos
        if gmail_token:
            from app.crud.user_crud import get_user_by_email
            user = get_user_by_email(db, email)
            if user:
                user.gmail_token = gmail_token
                db.commit()
                logger.info(f"Token de Gmail guardado para usuario: {email}")
        
        return TokenResponse(token=result["token"])
        
    except HTTPException as e:
        # Re-lanzar la excepción HTTP con el código de estado apropiado
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.post("/google/query", response_model=TokenResponse)
def autenticar_con_google_query(
    email: str = Query(..., description="Email del usuario autenticado con Google"),
    token: str = Query(..., description="Token de identificación de Google"),
    db: Session = Depends(get_db)
):
    """
    Endpoint POST /auth/google/query
    Endpoint alternativo para compatibilidad con aplicación Android
    Funciona igual que /auth/google
    """
    try:
        # Usar la misma función de autenticación
        result = authenticate_with_google(email, token, db)
        return TokenResponse(token=result["token"])
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.post("/google/gmail", response_model=TokenResponse)
def autenticar_con_google_gmail(
    email: str = Query(..., description="Email del usuario"),
    id_token: str = Query(..., description="ID Token de Google"),
    gmail_token: str = Query(..., description="Access Token de Google para Gmail"),
    db: Session = Depends(get_db)
):
    """
    Endpoint para autenticación con permisos de Gmail
    Guarda tanto el JWT interno como el access token de Gmail
    """
    try:
        # Verificar ID token como antes
        result = authenticate_with_google(email, id_token, db)
        
        # Buscar el usuario y guardar el token de Gmail
        from app.crud.user_crud import get_user_by_email
        user = get_user_by_email(db, email)
        if user:
            user.gmail_token = gmail_token
            db.commit()
            logger.info(f"Token de Gmail guardado para usuario: {email}")
        
        return TokenResponse(token=result["token"])
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.post("/update-gmail-token")
def actualizar_gmail_token(
    gmail_token: str = Query(..., description="Nuevo Access Token de Gmail"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualizar el token de Gmail del usuario autenticado
    """
    try:
        current_user.gmail_token = gmail_token
        db.commit()
        
        return {
            "message": "Token de Gmail actualizado correctamente",
            "user_email": current_user.email,
            "has_gmail_token": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar token de Gmail: {str(e)}"
        )

# Endpoints adicionales para compatibilidad y utilidad
@router.post("/legacy/token")
def crear_token_legacy():
    """Endpoint legacy para generar token básico"""
    try:
        # Crear un token básico sin datos específicos del usuario
        access_token = create_access_token(
            data={"sub": "legacy_user", "user_id": 0}
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar token legacy: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
def obtener_usuario_actual(current_user: User = Depends(get_current_user)):
    """Obtener información del usuario autenticado"""
    return current_user

@router.get("/validate")
def validar_sesion(current_user: User = Depends(get_current_user)):
    """Validar que el token de sesión sea válido"""
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "name": current_user.name
    }

@router.post("/debug/token")
def generar_token_debug():
    """
    Endpoint temporal para generar un token de prueba
    SOLO PARA DESARROLLO - REMOVER EN PRODUCCIÓN
    """
    try:
        # Crear token con datos de tu usuario
        access_token = create_test_token(
            email="marcosibarra1234@gmail.com",
            user_id=1
        )
        return {
            "token": access_token,
            "type": "bearer",
            "expires_in": 7 * 24 * 60 * 60,  # 7 días en segundos
            "instructions": "Copia este token y úsalo en Authorization: Bearer [token]"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar token: {str(e)}"
        )

@router.post("/simple-auth")
def autenticacion_simple(
    email: str = Query(..., description="Email del usuario"),
    db: Session = Depends(get_db)
):
    """
    Autenticación simple SIN verificar con Google (solo para desarrollo)
    """
    try:
        from app.crud.user_crud import get_or_create_user
        
        # Crear usuario sin verificar con Google
        user = get_or_create_user(
            db=db,
            email=email,
            google_id=f"dev_{email}",  # ID falso para desarrollo
            name="Usuario de Desarrollo",
            picture=None
        )
        
        # Crear JWT
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id}
        )
        
        return {
            "token": access_token,
            "message": "Autenticación de desarrollo exitosa",
            "warning": "Este endpoint NO verifica con Google"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )