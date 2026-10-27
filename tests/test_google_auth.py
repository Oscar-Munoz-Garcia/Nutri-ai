import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services import auth_service

client = TestClient(app)


@pytest.fixture
def google_configurado(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client.apps.googleusercontent.com")


def _simular_google(monkeypatch, **info):
    """Sustituye la verificación real de Google por un token ya 'verificado' con estos datos."""
    def falso(credential):
        if credential != "token-valido":
            raise HTTPException(status_code=401, detail="Token de Google inválido o caducado.")
        return info
    monkeypatch.setattr(auth_service, "verificar_token_google", falso)


def test_config_expone_client_id(google_configurado):
    res = client.get("/api/v1/auth/config")
    assert res.json() == {"google_client_id": "test-client.apps.googleusercontent.com"}


def test_google_sin_configurar_devuelve_503(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", None)
    res = client.post("/api/v1/auth/google", json={"credential": "token-valido"})
    assert res.status_code == 503


def test_google_crea_cuenta_sin_password_y_da_jwt(google_configurado, monkeypatch):
    email = f"ana_{uuid.uuid4().hex[:6]}@gmail.com"
    _simular_google(monkeypatch, email=email, email_verified=True, given_name="Ana")

    res = client.post("/api/v1/auth/google", json={"credential": "token-valido"})
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == email

    # La cuenta no tiene contraseña: el login clásico la rechaza
    res = client.post("/api/v1/auth/login", json={"username_or_email": email, "password": auth_service.SIN_PASSWORD_GOOGLE})
    assert res.status_code == 401

    # Segundo inicio de sesión: misma cuenta, no se duplica
    res2 = client.post("/api/v1/auth/google", json={"credential": "token-valido"})
    me2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {res2.json()['access_token']}"})
    assert me2.json()["id"] == me.json()["id"]


def test_google_entra_en_cuenta_existente_con_mismo_correo(google_configurado, monkeypatch):
    nombre = f"luis_{uuid.uuid4().hex[:6]}"
    email = f"{nombre}@test.com"
    reg = client.post("/api/v1/auth/registro", json={"username": nombre, "email": email, "password": "secreto123"})
    _simular_google(monkeypatch, email=email.upper(), email_verified=True)

    res = client.post("/api/v1/auth/google", json={"credential": "token-valido"})
    assert res.status_code == 200
    assert res.json()["username"] == reg.json()["username"]


def test_google_rechaza_token_invalido_y_correo_no_verificado(google_configurado, monkeypatch):
    _simular_google(monkeypatch, email="x@gmail.com", email_verified=False)
    assert client.post("/api/v1/auth/google", json={"credential": "falso"}).status_code == 401
    assert client.post("/api/v1/auth/google", json={"credential": "token-valido"}).status_code == 401


def test_verificacion_real_rechaza_token_basura(google_configurado):
    with pytest.raises(HTTPException) as exc:
        auth_service.verificar_token_google("esto.no.es-un-jwt")
    assert exc.value.status_code == 401
