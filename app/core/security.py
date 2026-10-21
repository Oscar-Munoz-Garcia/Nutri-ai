import os
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

SECRET_KEY = os.getenv("JWT_SECRET", "nutri_ai_super_secret_key_2026_dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Encripta la contraseña con Bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña ingresada coincide con el hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Genera un Token JWT con expiración."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decodifica y valida un Token JWT."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None