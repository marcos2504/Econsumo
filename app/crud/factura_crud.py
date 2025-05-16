from sqlalchemy.orm import Session
from app.models.factura_model import Factura

def get_facturas(db: Session):
    return db.query(Factura).all()