from sqlalchemy.orm import Session
from app.models.user_model import User
from app.schemas.user_schemas import UserCreate, UserUpdate
from typing import Optional

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_user_by_google_id(db: Session, google_id: str) -> Optional[User]:
    return db.query(User).filter(User.google_id == google_id).first()

def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(
        email=user.email,
        google_id=user.google_id,
        full_name=user.full_name,  # Usar full_name en lugar de name
        picture=user.picture,
        gmail_token=user.gmail_token,
        gmail_refresh_token=getattr(user, 'gmail_refresh_token', None)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user: User, user_update: UserUpdate) -> User:
    """Actualizar un usuario existente"""
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

def get_or_create_user(
    db: Session, 
    email: str, 
    google_id: str, 
    name: str, 
    picture: str = None, 
    gmail_token: str = None,
    gmail_refresh_token: str = None
) -> User:
    # Buscar por google_id primero
    user = get_user_by_google_id(db, google_id)
    if user:
        # Actualizar información si es necesario
        needs_update = False
        if user.email != email:
            user.email = email
            needs_update = True
        if user.full_name != name:
            user.full_name = name
            needs_update = True
        if user.picture != picture:
            user.picture = picture
            needs_update = True
        if gmail_token and user.gmail_token != gmail_token:
            user.gmail_token = gmail_token
            needs_update = True
        if gmail_refresh_token and user.gmail_refresh_token != gmail_refresh_token:
            user.gmail_refresh_token = gmail_refresh_token
            needs_update = True
            
        if needs_update:
            db.commit()
            db.refresh(user)
        return user
    
    # Si no existe, crear nuevo usuario
    user_data = UserCreate(
        email=email,
        google_id=google_id,
        full_name=name,
        picture=picture,
        gmail_token=gmail_token,
        gmail_refresh_token=gmail_refresh_token
    )
    return create_user(db, user_data)