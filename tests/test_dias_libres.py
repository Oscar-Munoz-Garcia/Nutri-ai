import uuid
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.models import RegistroConsumoDB, UsuarioDB
import app.services.streak_service as streak_service
from app.services.streak_service import _evaluar_dia

from tests.usuarios import crear_usuario

client = TestClient(app)

HOY = date.today()
LUNES = HOY - timedelta(days=HOY.weekday())


def _usuario():
    nombre = f"libre_{uuid.uuid4().hex[:8]}"
    headers = {"Authorization": f"Bearer {crear_usuario(nombre)}"}
    db = SessionLocal()
    try:
        uid = db.query(UsuarioDB).filter(UsuarioDB.username == nombre).first().id
    finally:
        db.close()
    return headers, uid


def test_proteina_cumple_con_margen_de_diez_por_ciento():
    assert _evaluar_dia(2000, 150, 2000, 150, True)["cumple_proteinas"]
    assert _evaluar_dia(2000, 136, 2000, 150, True)["cumple_proteinas"]      # -9,3%
    assert _evaluar_dia(2000, 164, 2000, 150, True)["cumple_proteinas"]      # +9,3%
    assert not _evaluar_dia(2000, 130, 2000, 150, True)["cumple_proteinas"]  # -13%
    assert not _evaluar_dia(2000, 170, 2000, 150, True)["cumple_proteinas"]  # +13%


def test_limite_semanal_de_dias_libres_desde_el_perfil():
    cab, _ = _usuario()
    semana = client.get("/api/v1/dias-libres", headers=cab).json()
    assert semana["limite"] == 1 and semana["usados"] == 0
    assert semana["semana_inicio"] == LUNES.isoformat()

    martes, miercoles = (LUNES + timedelta(days=1)).isoformat(), (LUNES + timedelta(days=2)).isoformat()
    assert client.put(f"/api/v1/dias-libres/{martes}", headers=cab, json={"libre": True}).json()["fechas"] == [martes]
    # El segundo de la misma semana supera el límite
    assert client.put(f"/api/v1/dias-libres/{miercoles}", headers=cab, json={"libre": True}).status_code == 409
    # Otra semana tiene su propio cupo
    otra = (LUNES + timedelta(days=9)).isoformat()
    assert client.put(f"/api/v1/dias-libres/{otra}", headers=cab, json={"libre": True}).status_code == 200

    # Subir el límite en el perfil permite marcar otro
    client.put("/api/v1/perfil", headers=cab, json={"modo_objetivo": "manual_calorias", "dias_libres_semana": 2})
    assert client.get("/api/v1/perfil", headers=cab).json()["dias_libres_semana"] == 2
    res = client.put(f"/api/v1/dias-libres/{miercoles}", headers=cab, json={"libre": True}).json()
    assert res["usados"] == 2 and res["limite"] == 2

    # Desmarcar libera el hueco y el resumen del día lo refleja
    client.put(f"/api/v1/dias-libres/{martes}", headers=cab, json={"libre": False})
    assert client.get(f"/api/v1/dias-libres?fecha={martes}", headers=cab).json()["fechas"] == [miercoles]
    assert client.get(f"/api/v1/diario/resumen?fecha={miercoles}", headers=cab).json()["dia_libre"] is True
    assert client.get(f"/api/v1/diario/resumen?fecha={martes}", headers=cab).json()["dia_libre"] is False

    assert client.put("/api/v1/dias-libres/no-es-fecha", headers=cab, json={"libre": True}).status_code == 422


def test_dia_libre_no_rompe_ni_suma_racha():
    cab, uid = _usuario()
    client.put("/api/v1/perfil", headers=cab, json={"modo_objetivo": "manual_calorias", "dias_libres_semana": 2})
    metas = client.get("/api/v1/diario/resumen", headers=cab).json()["objetivos"]
    cal, prot = metas["calorias_objetivo"], metas["proteinas_objetivo"]
    hoy = date(2001, 3, 10)  # sábado
    # 6 y 7 cumplen, el 8 es una comida fuera (se pasa), 9 cumple, hoy (10) libre
    dias = {"2001-03-06": (cal, prot), "2001-03-07": (cal, prot), "2001-03-08": (cal * 1.6, prot * 0.5),
            "2001-03-09": (cal, prot), "2001-03-10": (cal * 2, 20.0)}
    db = SessionLocal()
    try:
        for f, (c, p) in dias.items():
            db.add(RegistroConsumoDB(usuario_id=uid, fecha=f, nombre="test", calorias=c, proteinas=p, carbohidratos=0, grasas=0))
        db.commit()
    finally:
        db.close()

    assert streak_service.obtener_racha(uid, dias=7, hoy=hoy)["racha_actual"] == 1  # el 8 la rompe: solo cuenta el 9

    for f in ("2001-03-08", "2001-03-10"):
        assert client.put(f"/api/v1/dias-libres/{f}", headers=cab, json={"libre": True}).status_code == 200

    data = streak_service.obtener_racha(uid, dias=7, hoy=hoy)
    assert data["racha_actual"] == 3 and data["mejor_racha"] == 3
    assert data["dias_cumplidos"] == 3 and data["dias_registrados"] == 3 and data["dias_libres"] == 2
    por_fecha = {d["fecha"]: d for d in data["dias"]}
    assert por_fecha["2001-03-08"]["libre"] and not por_fecha["2001-03-09"]["libre"]
