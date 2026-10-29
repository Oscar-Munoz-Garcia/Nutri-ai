"""Fechas: consultar y registrar comidas en cualquier día (ayer o hace años) y años bisiestos (29 de febrero)."""
import uuid
from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.db.models import UsuarioDB
from app.services import export_service, streak_service

from tests.usuarios import crear_usuario

client = TestClient(app)


def _usuario():
    nombre = f"fechas_{uuid.uuid4().hex[:8]}"
    cab = {"Authorization": f"Bearer {crear_usuario(nombre)}"}
    db = SessionLocal()
    try:
        uid = db.query(UsuarioDB).filter(UsuarioDB.username == nombre).first().id
    finally:
        db.close()
    return cab, uid


def _comida(nombre, kcal=500, prot=30):
    return {"nombre": nombre, "calorias": kcal, "proteinas": prot, "carbohidratos": 50, "grasas": 15}


def test_registrar_y_consultar_un_dia_pasado():
    cab, _ = _usuario()
    res = client.post("/api/v1/diario/consumo?fecha=2019-06-15", headers=cab, json=_comida("Paella"))
    assert res.status_code == 200

    pasado = client.get("/api/v1/diario/resumen?fecha=2019-06-15", headers=cab).json()
    assert pasado["fecha"] == "2019-06-15"
    assert [r["nombre"] for r in pasado["registros"]] == ["Paella"]
    assert pasado["calorias_totales"] == 500

    # Lo de ese día no aparece hoy
    hoy = client.get("/api/v1/diario/resumen", headers=cab).json()
    assert hoy["fecha"] == date.today().isoformat()
    assert all(r["nombre"] != "Paella" for r in hoy["registros"])


def test_dia_pasado_usa_su_plan_y_su_dia_libre():
    cab, _ = _usuario()
    descanso = client.post("/api/v1/planes", headers=cab, json={
        "nombre": "Descanso", "calorias_objetivo": 1900, "proteinas_objetivo": 140,
        "carbohidratos_objetivo": 180, "grasas_objetivo": 60}).json()
    client.put("/api/v1/planes/calendario/2020-02-29", headers=cab, json={"plan_id": descanso["id"]})
    client.put("/api/v1/dias-libres/2020-02-29", headers=cab, json={"libre": True})

    dia = client.get("/api/v1/diario/resumen?fecha=2020-02-29", headers=cab).json()
    assert dia["plan"]["nombre"] == "Descanso"
    assert dia["objetivos"]["calorias_objetivo"] == 1900
    assert dia["dia_libre"] is True
    # El día siguiente vuelve al plan principal y no es libre
    siguiente = client.get("/api/v1/diario/resumen?fecha=2020-03-01", headers=cab).json()
    assert siguiente["plan"]["es_principal"] and siguiente["dia_libre"] is False


def test_29_de_febrero_solo_existe_en_anos_bisiestos():
    cab, _ = _usuario()
    for bisiesto in ["2024-02-29", "2000-02-29", "1996-02-29"]:
        assert client.post(f"/api/v1/diario/consumo?fecha={bisiesto}", headers=cab, json=_comida("Tarta")).status_code == 200
        assert client.get(f"/api/v1/diario/resumen?fecha={bisiesto}", headers=cab).json()["registros"][0]["nombre"] == "Tarta"
    # 1900 y 2100 son divisibles por 4 pero no son bisiestos (divisibles por 100 y no por 400)
    for invalida in ["2025-02-29", "1900-02-29", "2100-02-29", "2024-02-30", "2024-13-01", "ayer"]:
        assert client.get(f"/api/v1/diario/resumen?fecha={invalida}", headers=cab).status_code == 422
        assert client.post(f"/api/v1/diario/consumo?fecha={invalida}", headers=cab, json=_comida("X")).status_code == 422


def test_semana_con_29_de_febrero_va_de_lunes_a_domingo():
    cab, _ = _usuario()
    semana = client.get("/api/v1/planes/calendario?fecha=2024-02-29", headers=cab).json()
    assert [d["fecha"] for d in semana] == ["2024-02-26", "2024-02-27", "2024-02-28", "2024-02-29",
                                           "2024-03-01", "2024-03-02", "2024-03-03"]
    # En un año no bisiesto, del 28 de febrero se pasa al 1 de marzo
    semana = client.get("/api/v1/planes/calendario?fecha=2023-02-28", headers=cab).json()
    assert [d["fecha"] for d in semana] == ["2023-02-27", "2023-02-28", "2023-03-01", "2023-03-02",
                                           "2023-03-03", "2023-03-04", "2023-03-05"]
    libres = client.get("/api/v1/dias-libres?fecha=2024-03-03", headers=cab).json()
    assert (libres["semana_inicio"], libres["semana_fin"]) == ("2024-02-26", "2024-03-03")


def test_racha_cruza_el_29_de_febrero():
    cab, uid = _usuario()
    principal = client.get("/api/v1/planes", headers=cab).json()["planes"][0]
    kcal, prot = principal["calorias_objetivo"], principal["proteinas_objetivo"]
    for f in ["2024-02-27", "2024-02-28", "2024-02-29", "2024-03-01"]:
        client.post(f"/api/v1/diario/consumo?fecha={f}", headers=cab, json=_comida("Todo", kcal, prot))

    racha = streak_service.obtener_racha(uid, dias=14, hoy=date(2024, 3, 1))
    fechas = [d["fecha"] for d in racha["dias"]]
    assert "2024-02-29" in fechas and len(fechas) == len(set(fechas))
    assert fechas[0] == racha["desde"] and date.fromisoformat(racha["desde"]).weekday() == 0
    assert racha["racha_actual"] == 4

    # Año no bisiesto: el 28 de febrero va seguido del 1 de marzo
    racha = streak_service.obtener_racha(uid, dias=7, hoy=date(2023, 3, 1))
    fechas = [d["fecha"] for d in racha["dias"]]
    assert fechas[fechas.index("2023-02-28") + 1] == "2023-03-01"


def test_excel_de_un_ano_bisiesto_completo():
    _, uid = _usuario()
    # 2024 tiene 366 días y cabe entero; dos años seguidos no
    export_service.validar_rango(date(2024, 1, 1), date(2024, 12, 31))
    assert len(export_service.resumen_por_dia(uid, date(2024, 1, 1), date(2024, 12, 31))) == 366
    assert len(export_service.resumen_por_dia(uid, date(2023, 1, 1), date(2023, 12, 31))) == 365
    try:
        export_service.validar_rango(date(2024, 1, 1), date(2025, 1, 1))
        assert False, "un rango de 367 días debería rechazarse"
    except ValueError:
        pass
