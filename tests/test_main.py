import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text or "NUTRI.AI" in response.text


def test_pwa_manifest():
    response = client.get("/manifest.json")
    assert response.status_code == 200
    data = response.json()
    assert data.get("display") == "standalone"


def test_obtener_resumen_diario():
    response = client.get("/api/v1/diario/resumen")
    assert response.status_code == 200
    data = response.json()
    assert "calorias_totales" in data
    assert "objetivos" in data


def test_actualizar_objetivos_diarios():
    nuevos_objetivos = {
        "calorias_objetivo": 2400.0,
        "proteinas_objetivo": 170.0,
        "carbohidratos_objetivo": 220.0,
        "grasas_objetivo": 75.0
    }
    response = client.put("/api/v1/diario/objetivos", json=nuevos_objetivos)
    assert response.status_code == 200
    data = response.json()
    assert data["calorias_objetivo"] == 2400.0


def test_registrar_consumo_diario():
    nuevo_consumo = {
        "nombre": "Snack Proteico Test",
        "calorias": 250.0,
        "proteinas": 25.0,
        "carbohidratos": 15.0,
        "grasas": 5.0
    }
    response = client.post("/api/v1/diario/consumo", json=nuevo_consumo)
    assert response.status_code == 200
    data = response.json()
    assert data["nombre"] == "Snack Proteico Test"


def test_obtener_recetas():
    response = client.get("/api/v1/recetas")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_crear_receta():
    nueva_receta = {
        "nombre": "Batido Proteico de Avena",
        "descripcion": "Batido post-entreno rápido.",
        "calorias_totales": 320.0,
        "proteinas_totales": 30.0,
        "carbohidratos_totales": 35.0,
        "grasas_totales": 5.0,
        "tiempo_preparacion_min": 5,
        "utensilios_necesarios": ["Batidora"]
    }
    res_post = client.post("/api/v1/recetas", json=nueva_receta)
    assert res_post.status_code == 200
    data = res_post.json()
    assert data["nombre"] == "Batido Proteico de Avena"


def test_consumir_receta():
    recetas = client.get("/api/v1/recetas").json()
    if recetas:
        rec_id = recetas[0]["id"]
        res_consumo = client.post(f"/api/v1/recetas/{rec_id}/consumir")
        assert res_consumo.status_code == 200
        assert "status" in res_consumo.json()