import uuid
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.models import RegistroConsumoDB, PantryDB, PerfilDB
from app.core.config import settings
import app.services.streak_service as streak_service
import app.services.quicklog_service as quicklog_service

client = TestClient(app)


def _metas():
    db = SessionLocal()
    try:
        p = db.query(PerfilDB).filter(PerfilDB.id == 1).first()
        return (p.calorias_objetivo, p.proteinas_objetivo) if p else (2200.0, 160.0)
    finally:
        db.close()


def test_endpoint_racha_y_script_estatico():
    res = client.get("/api/v1/diario/racha?dias=30")
    assert res.status_code == 200
    data = res.json()
    assert data["hasta"] == date.today().isoformat()
    assert date.fromisoformat(data["desde"]).weekday() == 0
    assert {"racha_actual", "mejor_racha", "dias"} <= data.keys()

    assert client.get("/static/dashboard360.js").status_code == 200


def test_calculo_de_racha_con_fechas_aisladas():
    client.get("/api/v1/diario/resumen")  # garantiza que existe el perfil por defecto
    meta_cal, meta_prot = _metas()
    hoy = date(2001, 3, 10)
    # 5, 6 y 7 cumplen, el 8 se pasa de calorías, 9 cumple, hoy (10) aún sin cumplir
    dias = {
        "2001-03-05": (meta_cal, meta_prot), "2001-03-06": (meta_cal, meta_prot),
        "2001-03-07": (meta_cal, meta_prot), "2001-03-08": (meta_cal * 1.5, meta_prot),
        "2001-03-09": (meta_cal, meta_prot), "2001-03-10": (meta_cal * 0.3, 10.0),
    }
    db = SessionLocal()
    marca = f"test_racha_{uuid.uuid4().hex[:6]}"
    try:
        for f, (cal, prot) in dias.items():
            db.add(RegistroConsumoDB(fecha=f, nombre=marca, calorias=cal, proteinas=prot, carbohidratos=0, grasas=0))
        db.commit()

        data = streak_service.obtener_racha(dias=7, hoy=hoy)
        niveles = {d["fecha"]: d["nivel"] for d in data["dias"]}
        assert niveles["2001-03-05"] == 3
        assert niveles["2001-03-08"] == 2  # solo cumple proteína
        assert niveles["2001-03-10"] == 1
        assert niveles["2001-03-04"] == 0
        assert data["mejor_racha"] == 3
        assert data["racha_actual"] == 1  # hoy en curso no rompe la racha
    finally:
        db.query(RegistroConsumoDB).filter(RegistroConsumoDB.nombre == marca).delete()
        db.commit()
        db.close()


def test_separar_comida_y_alimentos():
    comida, resto = quicklog_service.separar_comida("Desayuno: 3 huevos cocidos y 80g de avena")
    assert comida == "Desayuno"
    assert quicklog_service.separar_alimentos(resto) == ["3 huevos cocidos", "80g de avena"]
    assert quicklog_service.separar_comida("200g de pollo") == (None, "200g de pollo")


def test_interpretar_usa_la_despensa_sin_groq(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    item_id = f"test_{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        db.add(PantryDB(id=item_id, nombre="Copos de avena zx", calorias_100g=380, proteinas_100g=13, carbohidratos_100g=60, grasas_100g=7))
        db.commit()

        res = client.post("/api/v1/diario/interpretar", json={"texto": "Cena: 50g de copos de avena zx y una manzana"})
        assert res.status_code == 200
        data = res.json()
        assert data["comida"] == "Cena"
        avena, manzana = data["items"]
        assert avena["origen"] == "despensa"
        assert avena["calorias"] == 190.0
        assert avena["nombre"].startswith("Cena · ")
        assert manzana["origen"] == "sin_estimar"
        assert data["avisos"]
    finally:
        db.query(PantryDB).filter(PantryDB.id == item_id).delete()
        db.commit()
        db.close()
