from app.core import security
from app.db.models import UsuarioDB, PerfilDB
from app.db.session import SessionLocal
from app.services.auth_service import SIN_PASSWORD_GOOGLE


def crear_usuario(nombre: str, email: str = None) -> str:
    """Crea un usuario con el registro ya completado (como tras entrar con Google) y devuelve su JWT."""
    db = SessionLocal()
    try:
        user = UsuarioDB(username=nombre, email=email or f"{nombre}@test.com", password_hash=SIN_PASSWORD_GOOGLE)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(PerfilDB(usuario_id=user.id, nombre=nombre, registro_completo=1))
        db.commit()
        return security.create_access_token({"sub": str(user.id), "username": user.username})
    finally:
        db.close()
