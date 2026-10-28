import os
import re
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, get_db
from app.db.models import UsuarioDB, PerfilDB
from app.models.auth import TokenResponse
from app.core import security
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/google", auto_error=False)

# Solo se entra con Google: la app no guarda contraseñas. La columna password_hash se mantiene
# (NOT NULL en las bases de datos existentes) con este valor fijo, que no es ningún hash.
SIN_PASSWORD_GOOGLE = "!google"


def verificar_token_google(credential: str) -> dict:
    """Valida el ID token de Google (firma, caducidad, emisor y audiencia = nuestro Client ID)."""
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests

    try:
        return id_token.verify_oauth2_token(credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de Google inválido o caducado.")


def _username_libre(db: Session, email: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9_.-]", "", email.split("@")[0]) or "usuario"
    candidato, n = base, 1
    while db.query(UsuarioDB).filter(UsuarioDB.username == candidato).first():
        n += 1
        candidato = f"{base}{n}"
    return candidato


def login_google(credential: str) -> TokenResponse:
    """Inicia sesión (o crea la cuenta) con Google y devuelve el JWT propio de la app."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="El inicio de sesión con Google no está configurado (falta GOOGLE_CLIENT_ID).")

    info = verificar_token_google(credential)
    email = (info.get("email") or "").lower()
    if not email or not info.get("email_verified"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tu cuenta de Google no tiene un correo verificado.")

    db = SessionLocal()
    try:
        # Si ya existe una cuenta con ese correo (Google lo ha verificado), se entra en ella
        user = db.query(UsuarioDB).filter(func.lower(UsuarioDB.email) == email).first()
        if not user:
            user = UsuarioDB(username=_username_libre(db, email), email=email, password_hash=SIN_PASSWORD_GOOGLE)
            db.add(user)
            db.commit()
            db.refresh(user)
            # Perfil pendiente del cuestionario de alta, precargado con el nombre de Google
            db.add(PerfilDB(
                usuario_id=user.id,
                nombre=info.get("given_name") or user.username,
                apellidos=info.get("family_name") or "",
                registro_completo=0
            ))
            db.commit()

        token = security.create_access_token({"sub": str(user.id), "username": user.username})
        return TokenResponse(access_token=token, username=user.username, registro_completo=registro_completo(user))
    finally:
        db.close()


def registro_completo(user: UsuarioDB) -> bool:
    return bool(user.perfil and user.perfil.registro_completo)


def obtener_usuario_actual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UsuarioDB:
    """Dependencia FastAPI para proteger endpoints y obtener el usuario activo."""
    if not token:
        if os.getenv("AUTH_DEMO_FALLBACK", "0") != "1":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Debes iniciar sesión.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        # Modo demo (solo tests/desarrollo con AUTH_DEMO_FALLBACK=1): usa el primer usuario
        user = db.query(UsuarioDB).order_by(UsuarioDB.id).first()
        if not user:
            user = UsuarioDB(username="oscar", email="oscar@nutri.ai", password_hash=SIN_PASSWORD_GOOGLE)
            db.add(user)
            db.commit()
            db.refresh(user)
            perfil = PerfilDB(usuario_id=user.id, nombre="Oscar", registro_completo=1)
            db.add(perfil)
            db.commit()
        return user

    payload = security.decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
    user = db.query(UsuarioDB).filter(UsuarioDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")

    return user