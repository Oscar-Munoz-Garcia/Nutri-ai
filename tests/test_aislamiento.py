import os
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import backup_service

client = TestClient(app)


def _registrar_usuario() -> dict:
    nombre = f"user_{uuid.uuid4().hex[:8]}"
    res = client.post("/api/v1/auth/registro", json={
        "username": nombre, "email": f"{nombre}@test.com", "password": "secreto123"
    })
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def ana():
    return _registrar_usuario()


@pytest.fixture
def luis():
    return _registrar_usuario()


def test_despensa_aislada_por_usuario(ana, luis):
    res = client.post("/api/v1/despensa", headers=ana, json={"nombre": "Avena Ana", "cantidad_gramos": 500})
    assert res.status_code == 200
    item_id = res.json()["id"]

    assert [i["nombre"] for i in client.get("/api/v1/despensa", headers=ana).json()] == ["Avena Ana"]
    assert client.get("/api/v1/despensa", headers=luis).json() == []

    # Luis no puede borrar la despensa de Ana
    assert client.delete(f"/api/v1/pantry/{item_id}", headers=luis).status_code == 404
    assert client.delete(f"/api/v1/pantry/{item_id}", headers=ana).status_code == 200
    assert client.get("/api/v1/despensa", headers=ana).json() == []


def test_despensa_suma_cantidad_mismo_nombre(ana):
    client.post("/api/v1/despensa", headers=ana, json={"nombre": "Arroz", "cantidad_gramos": 500})
    res = client.post("/api/v1/despensa", headers=ana, json={"nombre": "arroz ", "cantidad_gramos": 250})
    assert res.json()["cantidad_gramos"] == 750
    assert len(client.get("/api/v1/despensa", headers=ana).json()) == 1


def test_recetas_aisladas_y_conservan_ingredientes(ana, luis):
    receta = {
        "nombre": "Arroz con pollo", "calorias_totales": 600, "proteinas_totales": 45,
        "carbohidratos_totales": 70, "grasas_totales": 12, "utensilios_necesarios": ["Sartén"],
        "ingredientes": [{"nombre": "Arroz", "cantidad_gramos": 100}, {"nombre": "Pollo", "cantidad_gramos": 150}]
    }
    rec_id = client.post("/api/v1/recetas", headers=ana, json=receta).json()["id"]

    recetas_ana = client.get("/api/v1/recetas", headers=ana).json()
    assert len(recetas_ana) == 1
    assert recetas_ana[0]["ingredientes"][1] == {"nombre": "Pollo", "cantidad_gramos": 150}
    assert recetas_ana[0]["utensilios_necesarios"] == ["Sartén"]
    assert client.get("/api/v1/recetas", headers=luis).json() == []

    # Luis no puede consumir una receta de Ana
    assert client.post(f"/api/v1/recetas/{rec_id}/consumir", headers=luis).status_code == 404
    assert client.post(f"/api/v1/recetas/{rec_id}/consumir", headers=ana).status_code == 200
    assert client.get("/api/v1/diario/resumen", headers=ana).json()["calorias_totales"] == 600
    assert client.get("/api/v1/diario/resumen", headers=luis).json()["calorias_totales"] == 0


def test_diario_y_objetivos_aislados(ana, luis):
    consumo = {"nombre": "Huevos", "calorias": 210, "proteinas": 18, "carbohidratos": 1, "grasas": 15}
    reg = client.post("/api/v1/diario/consumo", headers=ana, json=consumo).json()
    assert reg["id"] is not None

    client.put("/api/v1/diario/objetivos", headers=ana, json={
        "calorias_objetivo": 3000, "proteinas_objetivo": 200, "carbohidratos_objetivo": 300, "grasas_objetivo": 90
    })

    resumen_ana = client.get("/api/v1/diario/resumen", headers=ana).json()
    resumen_luis = client.get("/api/v1/diario/resumen", headers=luis).json()
    assert [r["nombre"] for r in resumen_ana["registros"]] == ["Huevos"]
    assert resumen_ana["objetivos"]["calorias_objetivo"] == 3000
    assert resumen_luis["registros"] == []
    assert resumen_luis["objetivos"]["calorias_objetivo"] == 2200

    assert client.get("/api/v1/analitica/tendencias", headers=luis).json()["calorias"][-1] == 0
    assert client.get("/api/v1/analitica/tendencias", headers=ana).json()["calorias"][-1] == 210

    # Luis no puede borrar registros de Ana
    assert client.delete(f"/api/v1/diario/consumo/{reg['id']}", headers=luis).status_code == 404
    assert client.delete(f"/api/v1/diario/consumo/{reg['id']}", headers=ana).status_code == 200


def test_perfil_aislado(ana, luis):
    client.put("/api/v1/perfil", headers=ana, json={"nombre": "Ana", "modo_objetivo": "manual_calorias", "calorias_totales": 1800})
    assert client.get("/api/v1/perfil", headers=ana).json()["nombre"] == "Ana"
    assert client.get("/api/v1/perfil", headers=luis).json()["nombre"] != "Ana"


def test_sin_token_rechazado_si_no_hay_modo_demo(monkeypatch):
    monkeypatch.setenv("AUTH_DEMO_FALLBACK", "0")
    for metodo, ruta in [("get", "/api/v1/despensa"), ("get", "/api/v1/recetas"),
                         ("get", "/api/v1/diario/resumen"), ("get", "/api/v1/perfil")]:
        assert getattr(client, metodo)(ruta).status_code == 401
    assert client.get("/api/v1/despensa", headers={"Authorization": "Bearer token-falso"}).status_code == 401


def test_backup_crea_copia_y_limpia_antiguas(tmp_path):
    destino = tmp_path / "backups"
    destino.mkdir()
    antigua = destino / f"nutri_ai_{(datetime.now() - timedelta(days=30)).strftime('%Y%m%d_%H%M%S')}.db"
    antigua.write_bytes(b"")

    archivo = backup_service.crear_backup(destino)

    assert archivo.exists() and archivo.stat().st_size > 0
    assert not antigua.exists()
    assert backup_service.ultimo_backup_reciente(destino)
    import sqlite3
    with sqlite3.connect(archivo) as conn:
        tablas = {t for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"usuarios", "pantry", "recetas", "registros_consumo"} <= tablas


def test_filas_sin_dueno_solo_se_asignan_una_vez(tmp_path):
    from sqlalchemy import create_engine, text
    from app.db.session import Base
    from app.db.migrations import aplicar_migraciones

    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO usuarios (username, email, password_hash) VALUES ('oscar', 'o@x.com', 'h')"))
        conn.execute(text("INSERT INTO registros_consumo (fecha, nombre, calorias, proteinas, carbohidratos, grasas) "
                          "VALUES ('2026-01-01', 'antigua', 100, 1, 1, 1)"))

    aplicar_migraciones(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO usuarios (username, email, password_hash) VALUES ('ana', 'a@x.com', 'h')"))
        conn.execute(text("INSERT INTO registros_consumo (fecha, nombre, calorias, proteinas, carbohidratos, grasas) "
                          "VALUES ('2026-02-01', 'nueva_sin_dueno', 100, 1, 1, 1)"))
    aplicar_migraciones(engine)

    with engine.connect() as conn:
        filas = dict(conn.execute(text("SELECT nombre, usuario_id FROM registros_consumo")).all())
    assert filas == {"antigua": 1, "nueva_sin_dueno": None}
