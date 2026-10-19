import pytest
from fastapi.testclient import TestClient
from app.main import app

# Cliente de pruebas para FastAPI
client = TestClient(app)


# 1. Test de la página principal (HTML Dashboard)
def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text or "NutriAI" in response.text


# 2. Test del archivo Manifest PWA
def test_pwa_manifest():
    response = client.get("/manifest.json")
    assert response.status_code == 200
    data = response.json()
    assert data.get("display") == "standalone"
    assert data.get("short_name") == "NutriAI"


# 3. Test del endpoint de resumen del diario nutricional
def test_obtener_resumen_diario():
    response = client.get("/api/v1/diario/resumen")
    assert response.status_code == 200
    data = response.json()
    assert "calorias_totales" in data
    assert "proteinas_totales" in data


# 4. Test del catálogo de recetas
def test_obtener_recetas():
    response = client.get("/api/v1/recetas")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# 5. Test CRUD básico de la Despensa Virtual
def test_despensa_flow():
    nuevo_alimento = {
        "nombre": "Pechuga de Pavo Test",
        "cantidad_gramos": 250.0,
        "calorias_100g": 105.0,
        "proteinas_100g": 24.0,
        "carbohidratos_100g": 0.0,
        "grasas_100g": 1.0
    }
    
    # Insertar alimento de prueba
    res_post = client.post("/api/v1/despensa", json=nuevo_alimento)
    assert res_post.status_code == 200
    
    # Verificar que el alimento se guardó en la lista
    res_get = client.get("/api/v1/despensa")
    assert res_get.status_code == 200
    items = res_get.json()
    nombres = [item["nombre"] for item in items]
    assert "Pechuga de Pavo Test" in nombres

    # 6. Test de creación de receta personalizada
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
    assert "id" in data