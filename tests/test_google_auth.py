import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services import auth_service
from tests.usuarios import crear_usuario

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


def test_google_crea_cuenta_pendiente_de_cuestionario(google_configurado, monkeypatch):
    email = f"ana_{uuid.uuid4().hex[:6]}@gmail.com"
    _simular_google(monkeypatch, email=email, email_verified=True, given_name="Ana", family_name="López")

    res = client.post("/api/v1/auth/google", json={"credential": "token-valido"})
    assert res.status_code == 200, res.text
    assert res.json()["registro_completo"] is False
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}

    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["email"] == email and me["registro_completo"] is False
    perfil = client.get("/api/v1/perfil", headers=headers).json()
    assert (perfil["nombre"], perfil["apellidos"]) == ("Ana", "López")

    # Segundo inicio de sesión sin rellenar el cuestionario: misma cuenta y se vuelve a pedir
    res2 = client.post("/api/v1/auth/google", json={"credential": "token-valido"})
    assert res2.json()["registro_completo"] is False
    me2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {res2.json()['access_token']}"}).json()
    assert me2["id"] == me["id"]


def test_cuestionario_completa_registro_y_calcula_objetivos(google_configurado, monkeypatch):
    _simular_google(monkeypatch, email=f"luis_{uuid.uuid4().hex[:6]}@gmail.com", email_verified=True)
    token = client.post("/api/v1/auth/google", json={"credential": "token-valido"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    datos = {"nombre": "Luis", "apellidos": "García Pérez", "edad": 30, "peso_kg": 80, "altura_cm": 180,
             "genero": "hombre", "nivel_actividad": "moderado", "objetivo": "perder_grasa"}
    assert client.post("/api/v1/auth/completar-registro", json={**datos, "edad": 5}, headers=headers).status_code == 422

    res = client.post("/api/v1/auth/completar-registro", json=datos, headers=headers)
    assert res.status_code == 200, res.text
    perfil = res.json()
    assert perfil["apellidos"] == "García Pérez" and perfil["objetivo"] == "perder_grasa"
    # Mifflin-St Jeor: (800 + 1125 - 150 + 5) * 1.55 = 2759 kcal de mantenimiento, -400 por perder grasa
    assert perfil["objetivos_diarios"]["calorias_objetivo"] == 2359.0

    assert client.get("/api/v1/auth/me", headers=headers).json()["registro_completo"] is True
    assert [p["peso_kg"] for p in client.get("/api/v1/peso", headers=headers).json()] == [80.0]
    otra = client.post("/api/v1/auth/google", json={"credential": "token-valido"}).json()
    assert otra["registro_completo"] is True


def test_ya_no_existe_login_con_contrasena():
    assert client.post("/api/v1/auth/login", json={"username_or_email": "a", "password": "b"}).status_code in (404, 405)
    assert client.post("/api/v1/auth/registro", json={"username": "a", "email": "a@a.com", "password": "b"}).status_code in (404, 405)


def test_google_entra_en_cuenta_existente_con_mismo_correo(google_configurado, monkeypatch):
    nombre = f"luis_{uuid.uuid4().hex[:6]}"
    crear_usuario(nombre, email=f"{nombre}@test.com")
    _simular_google(monkeypatch, email=f"{nombre}@TEST.com", email_verified=True)

    res = client.post("/api/v1/auth/google", json={"credential": "token-valido"})
    assert res.status_code == 200
    assert res.json()["username"] == nombre
    assert res.json()["registro_completo"] is True


def test_google_rechaza_token_invalido_y_correo_no_verificado(google_configurado, monkeypatch):
    _simular_google(monkeypatch, email="x@gmail.com", email_verified=False)
    assert client.post("/api/v1/auth/google", json={"credential": "falso"}).status_code == 401
    assert client.post("/api/v1/auth/google", json={"credential": "token-valido"}).status_code == 401


def test_verificacion_real_rechaza_token_basura(google_configurado):
    with pytest.raises(HTTPException) as exc:
        auth_service.verificar_token_google("esto.no.es-un-jwt")
    assert exc.value.status_code == 401
