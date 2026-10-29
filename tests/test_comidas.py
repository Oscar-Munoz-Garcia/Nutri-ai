from fastapi.testclient import TestClient
from app.main import app

from tests.usuarios import crear_usuario

client = TestClient(app)


def _cab(token):
    return {"Authorization": f"Bearer {token}"}


def _plan(nombre, comidas=None):
    datos = {"nombre": nombre, "calorias_objetivo": 2300, "proteinas_objetivo": 180,
             "carbohidratos_objetivo": 250, "grasas_objetivo": 70}
    if comidas is not None:
        datos["comidas"] = comidas
    return datos


def test_cada_plan_tiene_sus_comidas_con_nombre():
    cab = _cab(crear_usuario("comidas_planes"))
    principal = client.get("/api/v1/planes", headers=cab).json()["planes"][0]
    # Sin elegir nada: desayuno, comida y cena
    assert principal["comidas"] == ["Desayuno", "Comida", "Cena"]

    entreno = client.post("/api/v1/planes", headers=cab,
                          json=_plan("Entreno", [" Comida ", "Pre-entreno", "Cena"])).json()
    assert entreno["comidas"] == ["Comida", "Pre-entreno", "Cena"]

    # Editar sin enviar comidas las deja como estaban; enviarlas las cambia
    editado = client.put(f"/api/v1/planes/{entreno['id']}", headers=cab, json=_plan("Entreno")).json()
    assert editado["comidas"] == ["Comida", "Pre-entreno", "Cena"]
    cinco = ["Desayuno", "Almuerzo", "Comida", "Merienda", "Cena"]
    editado = client.put(f"/api/v1/planes/{entreno['id']}", headers=cab, json=_plan("Entreno", cinco)).json()
    assert editado["comidas"] == cinco

    # Entre 1 y 8 comidas, sin nombres vacíos
    assert client.post("/api/v1/planes", headers=cab, json=_plan("X", [])).status_code == 422
    assert client.post("/api/v1/planes", headers=cab, json=_plan("X", ["C"] * 9)).status_code == 422
    assert client.post("/api/v1/planes", headers=cab, json=_plan("X", ["Comida", "  "])).status_code == 422


def test_perfil_y_cuestionario_eligen_las_comidas_del_plan_principal():
    cab = _cab(crear_usuario("comidas_perfil"))
    perfil = client.post("/api/v1/auth/completar-registro", headers=cab, json={
        "nombre": "Ana", "apellidos": "Pérez", "edad": 30, "peso_kg": 60, "altura_cm": 165,
        "genero": "mujer", "nivel_actividad": "moderado", "objetivo": "mantenimiento",
        "comidas": ["Desayuno", "Comida", "Merienda", "Cena"]
    }).json()
    assert perfil["comidas"] == ["Desayuno", "Comida", "Merienda", "Cena"]

    # Modo automático: se recalculan las metas y se cambian las comidas
    perfil = client.put("/api/v1/perfil", headers=cab, json={
        "modo_objetivo": "manual_calorias", "calorias_totales": 2000, "comidas": ["Comida", "Cena"]}).json()
    assert perfil["comidas"] == ["Comida", "Cena"]
    assert perfil["objetivos_diarios"]["calorias_objetivo"] == 2000
    # Guardar el perfil sin comidas no las toca
    perfil = client.put("/api/v1/perfil", headers=cab, json={"modo_objetivo": "manual_calorias"}).json()
    assert perfil["comidas"] == ["Comida", "Cena"]

    resumen = client.get("/api/v1/diario/resumen", headers=cab).json()
    assert resumen["plan"]["comidas"] == ["Comida", "Cena"]


def test_alimentos_por_gramos_y_comida_en_el_diario():
    cab = _cab(crear_usuario("comidas_diario"))
    for registro in [
        {"nombre": "Arroz blanco cocido", "calorias": 260, "proteinas": 5.4, "carbohidratos": 56.4,
         "grasas": 0.6, "gramos": 200, "comida": "Comida"},
        {"nombre": "Pechuga de pollo cruda", "calorias": 165, "proteinas": 34.7, "carbohidratos": 0,
         "grasas": 2.4, "gramos": 150, "comida": "Comida"},
        {"nombre": "Café", "calorias": 5, "proteinas": 0, "carbohidratos": 0, "grasas": 0},
    ]:
        assert client.post("/api/v1/diario/consumo", headers=cab, json=registro).status_code == 200

    registros = client.get("/api/v1/diario/resumen", headers=cab).json()["registros"]
    assert [(r["comida"], r["gramos"]) for r in registros] == [("Comida", 200), ("Comida", 150), (None, None)]
    assert client.post("/api/v1/diario/consumo", headers=cab, json={
        "nombre": "X", "calorias": 1, "proteinas": 0, "carbohidratos": 0, "grasas": 0, "gramos": 0}).status_code == 422


def test_buscador_de_alimentos_despensa_primero():
    cab = _cab(crear_usuario("comidas_buscar"))
    assert client.post("/api/v1/despensa", headers=cab, json={
        "nombre": "Arroz basmati Brillante", "cantidad_gramos": 1000, "calorias_100g": 350,
        "proteinas_100g": 8, "carbohidratos_100g": 77, "grasas_100g": 1}).status_code == 200

    res = client.get("/api/v1/alimentos/buscar", headers=cab, params={"q": "arroz"}).json()
    assert res[0]["origen"] == "despensa" and res[0]["nombre"] == "Arroz basmati Brillante"
    assert any(r["nombre"] == "Arroz blanco cocido" and r["origen"] == "base" for r in res)

    # Sin tildes, varias palabras y en inglés
    assert client.get("/api/v1/alimentos/buscar", headers=cab, params={"q": "platano"}).json()[0]["nombre"] == "Plátano"
    pollo = client.get("/api/v1/alimentos/buscar", headers=cab, params={"q": "pollo plancha"}).json()
    assert [r["nombre"] for r in pollo] == ["Pechuga de pollo a la plancha"]
    assert client.get("/api/v1/alimentos/buscar", headers=cab, params={"q": "crushed tomato"}).json()[0]["nombre"] == "Tomate triturado"
    assert client.get("/api/v1/alimentos/buscar", headers=cab, params={"q": ""}).json() == []
    # La despensa de otro usuario no aparece
    otro = _cab(crear_usuario("comidas_buscar_otro"))
    assert all(r["origen"] == "base" for r in client.get("/api/v1/alimentos/buscar", headers=otro, params={"q": "arroz"}).json())
