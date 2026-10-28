from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional


class UsuarioRegistro(BaseModel):
    username: str
    email: EmailStr
    password: str


class UsuarioLogin(BaseModel):
    username_or_email: str
    password: str


class LoginGoogle(BaseModel):
    credential: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str