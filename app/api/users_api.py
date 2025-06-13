from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.user_model import User
from app.schemas.user_schemas import UserResponse
from app.services.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
def listar_usuarios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar todos los usuarios registrados
    Solo usuarios autenticados pueden acceder
    """
    try:
        usuarios = db.query(User).all()
        return usuarios
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener usuarios: {str(e)}"
        )

@router.get("/{user_id}", response_model=UserResponse)
def obtener_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener un usuario específico por ID
    """
    try:
        usuario = db.query(User).filter(User.id == user_id).first()
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        return usuario
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener usuario: {str(e)}"
        )

@router.delete("/{user_id}")
def eliminar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Eliminar un usuario específico por ID
    También elimina todas sus facturas e histórico de consumo relacionado
    """
    try:
        # Buscar el usuario
        usuario = db.query(User).filter(User.id == user_id).first()
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Prevenir auto-eliminación por seguridad
        if usuario.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes eliminar tu propio usuario"
            )
        
        # Importar modelos necesarios
        from app.models.factura_model import Factura
        from app.models.historico_model import HistoricoConsumo
        
        # Eliminar histórico de consumo relacionado con las facturas del usuario
        facturas_usuario = db.query(Factura).filter(Factura.user_id == user_id).all()
        for factura in facturas_usuario:
            db.query(HistoricoConsumo).filter(HistoricoConsumo.factura_id == factura.id).delete()
        
        # Eliminar facturas del usuario
        facturas_eliminadas = db.query(Factura).filter(Factura.user_id == user_id).count()
        db.query(Factura).filter(Factura.user_id == user_id).delete()
        
        # Eliminar el usuario
        db.delete(usuario)
        db.commit()
        
        return {
            "message": "Usuario eliminado exitosamente",
            "user_id": user_id,
            "email": usuario.email,
            "facturas_eliminadas": facturas_eliminadas,
            "eliminado_por": current_user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar usuario: {str(e)}"
        )

@router.delete("/me/delete-account")
def eliminar_mi_cuenta(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Eliminar la cuenta del usuario autenticado
    ¡CUIDADO! Esta acción es irreversible
    """
    try:
        from app.models.factura_model import Factura
        from app.models.historico_model import HistoricoConsumo
        
        # Eliminar histórico de consumo
        facturas_usuario = db.query(Factura).filter(Factura.user_id == current_user.id).all()
        historico_eliminado = 0
        for factura in facturas_usuario:
            count = db.query(HistoricoConsumo).filter(HistoricoConsumo.factura_id == factura.id).count()
            historico_eliminado += count
            db.query(HistoricoConsumo).filter(HistoricoConsumo.factura_id == factura.id).delete()
        
        # Eliminar facturas
        facturas_eliminadas = db.query(Factura).filter(Factura.user_id == current_user.id).count()
        db.query(Factura).filter(Factura.user_id == current_user.id).delete()
        
        # Guardar email antes de eliminar
        email_eliminado = current_user.email
        
        # Eliminar usuario
        db.delete(current_user)
        db.commit()
        
        return {
            "message": "Tu cuenta ha sido eliminada exitosamente",
            "email": email_eliminado,
            "facturas_eliminadas": facturas_eliminadas,
            "historico_eliminado": historico_eliminado,
            "warning": "Esta acción es irreversible"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar cuenta: {str(e)}"
        )

@router.get("/stats/resumen")
def estadisticas_usuarios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener estadísticas generales de usuarios
    """
    try:
        total_usuarios = db.query(User).count()
        usuarios_activos = db.query(User).filter(User.is_active == True).count()
        usuarios_inactivos = total_usuarios - usuarios_activos
        
        return {
            "total_usuarios": total_usuarios,
            "usuarios_activos": usuarios_activos,
            "usuarios_inactivos": usuarios_inactivos
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )