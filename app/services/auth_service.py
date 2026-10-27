import os
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, get_db
from app.db.models import UsuarioDB, PerfilDB
from app.models.auth import UsuarioRegistro, UsuarioLogin, TokenResponse, UsuarioOut
from app.core import security

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def registrar_usuario(datos: UsuarioRegistro) -> TokenResponse:
    db = SessionLocal()
    try:
        # Validar si ya existe
        user_exist = db.query(UsuarioDB).filter(
            (UsuarioDB.username == datos.username) | (UsuarioDB.email == datos.email)
        ).first()
        if user_exist:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario o correo ya está registrado."
            )

        # Crear Usuario con password hasheado
        pwd_hash = security.hash_password(datos.password)
        nuevo_usuario = UsuarioDB(
            username=datos.username,
            email=datos.email,
            password_hash=pwd_hash
        )
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)

        # Crear Perfil por defecto asociado al usuario
        perfil_defecto = PerfilDB(
            usuario_id=nuevo_usuario.id,
            nombre=datos.username
        )
        db.add(perfil_defecto)
        db.commit()

        # Generar token
        token = security.create_access_token({"sub": str(nuevo_usuario.id), "username": nuevo_usuario.username})
        return TokenResponse(access_token=token, username=nuevo_usuario.username)
    finally:
        db.close()


def autenticar_usuario(datos: UsuarioLogin) -> TokenResponse:
    db = SessionLocal()
    try:
        user = db.query(UsuarioDB).filter(
            (UsuarioDB.username == datos.username_or_email) | (UsuarioDB.email == datos.username_or_email)
        ).first()

        if not user or not security.verify_password(datos.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos."
            )

        token = security.create_access_token({"sub": str(user.id), "username": user.username})
        return TokenResponse(access_token=token, username=user.username)
    finally:
        db.close()


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
            pwd_hash = security.hash_password("123456")
            user = UsuarioDB(username="oscar", email="oscar@nutri.ai", password_hash=pwd_hash)
            db.add(user)
            db.commit()
            db.refresh(user)
            perfil = PerfilDB(usuario_id=user.id, nombre="Oscar")
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