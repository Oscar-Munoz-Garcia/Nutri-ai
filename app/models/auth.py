from pydantic import BaseModel, ConfigDict
from typing import Optional


class LoginGoogle(BaseModel):
    credential: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    registro_completo: bool = True


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    registro_completo: bool = True