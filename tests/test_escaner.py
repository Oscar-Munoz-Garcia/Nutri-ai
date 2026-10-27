import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.models.food import ProductoNutricional
from app.models.recipe import Receta
import app.services.vision_service as vision_service
import app.services.openfoodfacts_service as openfoodfacts_service
import app.services.shopping_service as shopping_service
import app.services.recipe_service as recipe_service

client = TestClient(app)

IMAGEN = {"file": ("plato.jpg", b"\xff\xd8\xff fake jpeg", "image/jpeg")}


def test_vision_ocr_modo_prueba(monkeypatch):
    monkeypatch.setattr(vision_service.settings, "GROQ_API_KEY", None)
    response = client.post("/api/v1/alimentos/vision-ocr", files=IMAGEN)
    assert response.status_code == 200
    assert response.json()["calorias_100g"] == 210.0


def test_analizar_plato_modo_prueba(monkeypatch):
    monkeypatch.setattr(vision_service.settings, "GROQ_API_KEY", None)
    response = client.post("/api/v1/alimentos/analizar-plato", files=IMAGEN)
    assert response.status_code == 200
    data = response.json()
    assert data["modo_prueba"] is True
    assert len(data["ingredientes"]) == 3
    assert data["calorias_totales"] == round(sum(i["calorias"] for i in data["ingredientes"]), 1)


def test_analizar_plato_recalcula_totales_de_groq(monkeypatch):
    monkeypatch.setattr(vision_service.settings, "GROQ_API_KEY", "clave-test")

    async def groq_falso(prompt, imagen_b64, content_type, max_tokens=500):
        return {
            "nombre_plato": "Arroz con pollo",
            "ingredientes": [
                {"nombre": "Arroz", "peso_estimado_g": 150, "calorias": 195, "proteinas": 4, "carbohidratos": 42, "grasas": 0.5},
                {"nombre": "Pollo", "peso_estimado_g": "100", "calorias": 165, "proteinas": 31, "carbohidratos": 0, "grasas": 3.6},
                {"peso_estimado_g": 10}
            ],
            "confianza": 0.8,
            "notas": "Aceite no visible"
        }, ""

    monkeypatch.setattr(vision_service, "_consultar_groq_vision", groq_falso)
    data = client.post("/api/v1/alimentos/analizar-plato", files=IMAGEN).json()
    assert data["nombre_plato"] == "Arroz con pollo"
    assert len(data["ingredientes"]) == 2
    assert data["peso_total_g"] == 250.0
    assert data["calorias_totales"] == 360.0
    assert data["proteinas_totales"] == 35.0


def test_barcode_codigo_invalido():
    assert client.get("/api/v1/alimentos/barcode/12ab").status_code == 422


def test_barcode_encontrado_y_no_encontrado(monkeypatch):
    async def off_falso(codigo):
        if codigo == "3017620422003":
            return ProductoNutricional(codigo_barras=codigo, nombre="Nutella", calorias_100g=539.0)
        return None

    monkeypatch.setattr(openfoodfacts_service, "consultar_open_food_facts", off_falso)
    ok = client.get("/api/v1/alimentos/barcode/3017620422003")
    assert ok.status_code == 200
    assert ok.json()["nombre"] == "Nutella"
    assert client.get("/api/v1/alimentos/barcode/00000000").status_code == 404


def test_open_food_facts_convierte_kj(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"status": 1, "product": {
            "product_name_es": "Galletas",
            "brands": "Marca",
            "nutriments": {"energy-kj_100g": 2092, "proteins_100g": 6, "carbohydrates_100g": 70, "fat_100g": 20}
        }})

    cliente_real = httpx.AsyncClient
    monkeypatch.setattr(openfoodfacts_service.httpx, "AsyncClient",
                        lambda **kw: cliente_real(transport=httpx.MockTransport(handler), **kw))
    import asyncio
    producto = asyncio.run(openfoodfacts_service.consultar_open_food_facts("8410000000000"))
    assert producto.nombre == "Galletas"
    assert producto.calorias_100g == 500.0


def test_lista_compra_compara_recetas_con_despensa(monkeypatch):
    recetas = [
        Receta(id="r1", nombre="Pollo con arroz", calorias_totales=500, proteinas_totales=40,
               carbohidratos_totales=50, grasas_totales=10,
               ingredientes=[{"nombre": "Pechuga de pollo", "cantidad_gramos": 200},
                             {"nombre": "Arroz", "cantidad_gramos": 80}]),
        Receta(id="r2", nombre="Batido", calorias_totales=300, proteinas_totales=30,
               carbohidratos_totales=30, grasas_totales=5,
               ingredientes=[{"nombre": "Plátano", "cantidad_gramos": 120}]),
        Receta(id="r3", nombre="Sin datos", calorias_totales=100, proteinas_totales=1,
               carbohidratos_totales=1, grasas_totales=1),
    ]
    monkeypatch.setattr(recipe_service, "obtener_todas_las_recetas", lambda *a, **k: recetas)
    monkeypatch.setattr(shopping_service, "_leer_despensa",
                        lambda usuario_id: {"pechuga de pollo": 250.0, "platano": 500.0, "arroz basmati": 100.0})

    response = client.post("/api/v1/compra/lista", json={"recetas": [
        {"receta_id": "r1", "raciones": 3},
        {"receta_id": "r2", "raciones": 2},
        {"receta_id": "r3"},
        {"receta_id": "no-existe"},
    ]})
    assert response.status_code == 200
    data = response.json()

    faltantes = {i["nombre"]: i for i in data["faltantes"]}
    cubiertos = {i["nombre"]: i for i in data["cubiertos"]}
    assert faltantes["Pechuga de pollo"]["comprar_g"] == 350.0
    assert faltantes["Arroz"]["comprar_g"] == 140.0
    assert cubiertos["Plátano"]["disponible_g"] == 500.0
    assert data["recetas_sin_ingredientes"] == ["Sin datos"]
    assert data["recetas_no_encontradas"] == ["no-existe"]


def test_lista_compra_requiere_recetas():
    assert client.post("/api/v1/compra/lista", json={"recetas": []}).status_code == 422
