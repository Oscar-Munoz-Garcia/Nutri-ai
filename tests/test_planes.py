from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app

from tests.usuarios import crear_usuario

client = TestClient(app)

HOY = date.today()
LUNES = HOY - timedelta(days=HOY.weekday())


def _cab(token):
    return {"Authorization": f"Bearer {token}"}


def _plan(nombre, kcal, prot=150.0):
    return {"nombre": nombre, "calorias_objetivo": kcal, "proteinas_objetivo": prot,
            "carbohidratos_objetivo": 250.0, "grasas_objetivo": 70.0}


def test_plan_principal_sale_del_perfil_y_se_sincroniza():
    cab = _cab(crear_usuario("planes_principal"))
    client.put("/api/v1/perfil", headers=cab, json={"modo_objetivo": "manual_calorias", "calorias_totales": 2100})
    planes = client.get("/api/v1/planes", headers=cab).json()
    assert len(planes["planes"]) == 1
    principal = planes["planes"][0]
    assert principal["es_principal"] and principal["calorias_objetivo"] == 2100
    assert planes["semana"] == [principal["id"]] * 7

    # Editar el plan principal cambia las metas del perfil
    client.put(f"/api/v1/planes/{principal['id']}", headers=cab, json=_plan("Base", 2050))
    assert client.get("/api/v1/perfil", headers=cab).json()["objetivos_diarios"]["calorias_objetivo"] == 2050
    # Y no se puede borrar
    assert client.delete(f"/api/v1/planes/{principal['id']}", headers=cab).status_code == 400


def test_plan_por_dia_de_la_semana_y_cambio_puntual():
    cab = _cab(crear_usuario("planes_semana"))
    principal_id = client.get("/api/v1/planes", headers=cab).json()["planes"][0]["id"]
    entreno = client.post("/api/v1/planes", headers=cab, json=_plan("Entrenamiento", 2300, 180)).json()
    descanso = client.post("/api/v1/planes", headers=cab, json=_plan("Descanso", 2000)).json()

    # Entreno todos los días salvo hoy, que es de descanso
    semana = [entreno["id"]] * 7
    semana[HOY.weekday()] = descanso["id"]
    res = client.put("/api/v1/planes/semana", headers=cab, json={"semana": semana})
    assert res.json()["semana"] == semana

    resumen = client.get("/api/v1/diario/resumen", headers=cab).json()
    assert resumen["plan"]["nombre"] == "Descanso"
    assert resumen["objetivos"]["calorias_objetivo"] == 2000

    # Engranaje: hoy toca entreno solo esta vez
    dia = client.put(f"/api/v1/planes/calendario/{HOY.isoformat()}", headers=cab,
                     json={"plan_id": entreno["id"]}).json()
    assert dia["cambiado"] and dia["plan_semanal_id"] == descanso["id"]
    resumen = client.get("/api/v1/diario/resumen", headers=cab).json()
    assert resumen["objetivos"]["calorias_objetivo"] == 2300
    assert client.get("/api/v1/diario/racha", headers=cab).json()["meta_calorias"] == 2300

    # El mismo día de la semana que viene sigue con su plan semanal
    calendario = client.get("/api/v1/planes/calendario", headers=cab,
                            params={"fecha": (HOY + timedelta(days=7)).isoformat()}).json()
    assert calendario[HOY.weekday()]["plan_id"] == descanso["id"]
    assert calendario[0]["fecha"] == (LUNES + timedelta(days=7)).isoformat()

    # Volver al plan de la semana
    dia = client.put(f"/api/v1/planes/calendario/{HOY.isoformat()}", headers=cab, json={"plan_id": None}).json()
    assert not dia["cambiado"] and dia["plan_id"] == descanso["id"]

    # Borrar un plan devuelve sus días al principal
    client.delete(f"/api/v1/planes/{descanso['id']}", headers=cab)
    assert client.get("/api/v1/planes", headers=cab).json()["semana"][HOY.weekday()] == principal_id


def test_racha_y_versus_puntuan_cada_dia_con_su_plan():
    cab = _cab(crear_usuario("planes_racha"))
    descanso = client.post("/api/v1/planes", headers=cab, json=_plan("Descanso", 1800, 100)).json()
    client.put(f"/api/v1/planes/calendario/{HOY.isoformat()}", headers=cab, json={"plan_id": descanso["id"]})
    client.post("/api/v1/diario/consumo", headers=cab,
                json={"nombre": "Día de descanso", "calorias": 1800, "proteinas": 100, "carbohidratos": 200, "grasas": 60})

    hoy = client.get("/api/v1/diario/racha", headers=cab).json()["dias"][-1]
    assert hoy["nivel"] == 3 and hoy["plan"] == "Descanso"
    yo = next(p for p in client.get("/api/v1/versus", headers=cab).json()["participantes"] if p["es_yo"])
    assert yo["dias"][-1]["puntuacion"] == 100.0


def test_planes_aislados_por_usuario():
    cab_a = _cab(crear_usuario("planes_ana"))
    cab_b = _cab(crear_usuario("planes_beto"))
    plan_a = client.post("/api/v1/planes", headers=cab_a, json=_plan("Secreto", 2500)).json()

    assert all(p["id"] != plan_a["id"] for p in client.get("/api/v1/planes", headers=cab_b).json()["planes"])
    assert client.put(f"/api/v1/planes/{plan_a['id']}", headers=cab_b, json=_plan("Robado", 1)).status_code == 404
    assert client.delete(f"/api/v1/planes/{plan_a['id']}", headers=cab_b).status_code == 404
    res = client.put(f"/api/v1/planes/calendario/{HOY.isoformat()}", headers=cab_b, json={"plan_id": plan_a["id"]})
    assert res.status_code == 404
    semana_b = client.get("/api/v1/planes", headers=cab_b).json()["semana"]
    semana_b[0] = plan_a["id"]
    assert client.put("/api/v1/planes/semana", headers=cab_b, json={"semana": semana_b}).status_code == 404
