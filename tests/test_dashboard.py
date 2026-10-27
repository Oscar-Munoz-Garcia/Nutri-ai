import uuid
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.models import RegistroConsumoDB, PantryDB, UsuarioDB
from app.core.config import settings
import app.services.streak_service as streak_service
import app.services.quicklog_service as quicklog_service

client = TestClient(app)


def _registrar_usuario():
    nombre = f"dash_{uuid.uuid4().hex[:8]}"
    res = client.post("/api/v1/auth/registro", json={
        "username": nombre, "email": f"{nombre}@test.com", "password": "secreto123"
    })
    assert res.status_code == 200, res.text
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    db = SessionLocal()
    try:
        uid = db.query(UsuarioDB).filter(UsuarioDB.username == nombre).first().id
    finally:
        db.close()
    return headers, uid


def test_endpoint_racha_y_script_estatico():
    headers, _ = _registrar_usuario()
    res = client.get("/api/v1/diario/racha?dias=30", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["hasta"] == date.today().isoformat()
    assert date.fromisoformat(data["desde"]).weekday() == 0
    assert {"racha_actual", "mejor_racha", "dias"} <= data.keys()

    assert client.get("/static/dashboard360.js").status_code == 200


def test_calculo_de_racha_por_usuario():
    headers, uid = _registrar_usuario()
    _, otro_uid = _registrar_usuario()
    metas = client.get("/api/v1/diario/resumen", headers=headers).json()["objetivos"]
    meta_cal, meta_prot = metas["calorias_objetivo"], metas["proteinas_objetivo"]
    hoy = date(2001, 3, 10)
    # 5, 6 y 7 cumplen, el 8 se pasa de calorías, 9 cumple, hoy (10) aún sin cumplir
    dias = {
        "2001-03-05": (meta_cal, meta_prot), "2001-03-06": (meta_cal, meta_prot),
        "2001-03-07": (meta_cal, meta_prot), "2001-03-08": (meta_cal * 1.5, meta_prot),
        "2001-03-09": (meta_cal, meta_prot), "2001-03-10": (meta_cal * 0.3, 10.0),
    }
    db = SessionLocal()
    try:
        for f, (cal, prot) in dias.items():
            db.add(RegistroConsumoDB(usuario_id=uid, fecha=f, nombre="test", calorias=cal, proteinas=prot, carbohidratos=0, grasas=0))
        db.commit()
    finally:
        db.close()

    data = streak_service.obtener_racha(uid, dias=7, hoy=hoy)
    niveles = {d["fecha"]: d["nivel"] for d in data["dias"]}
    assert niveles["2001-03-05"] == 3
    assert niveles["2001-03-08"] == 2  # solo cumple proteína
    assert niveles["2001-03-10"] == 1
    assert niveles["2001-03-04"] == 0
    assert data["mejor_racha"] == 3
    assert data["racha_actual"] == 1  # hoy en curso no rompe la racha

    # Los registros de un usuario no cuentan en la racha de otro
    assert streak_service.obtener_racha(otro_uid, dias=7, hoy=hoy)["dias_registrados"] == 0


def test_separar_comida_y_alimentos():
    comida, resto = quicklog_service.separar_comida("Desayuno: 3 huevos cocidos y 80g de avena")
    assert comida == "Desayuno"
    assert quicklog_service.separar_alimentos(resto) == ["3 huevos cocidos", "80g de avena"]
    assert quicklog_service.separar_comida("200g de pollo") == (None, "200g de pollo")


def test_interpretar_usa_la_despensa_del_usuario_sin_groq(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    headers, uid = _registrar_usuario()
    otro_headers, _ = _registrar_usuario()
    db = SessionLocal()
    try:
        db.add(PantryDB(id=f"t_{uuid.uuid4().hex[:6]}", usuario_id=uid, nombre="Copos de avena zx",
                        calorias_100g=380, proteinas_100g=13, carbohidratos_100g=60, grasas_100g=7))
        db.commit()
    finally:
        db.close()

    texto = {"texto": "Cena: 50g de copos de avena zx y una manzana"}
    data = client.post("/api/v1/diario/interpretar", headers=headers, json=texto).json()
    assert data["comida"] == "Cena"
    avena, manzana = data["items"]
    assert avena["origen"] == "despensa"
    assert avena["calorias"] == 190.0
    assert avena["nombre"].startswith("Cena · ")
    assert manzana["origen"] == "sin_estimar"
    assert data["avisos"]

    # Otro usuario no ve esa despensa
    otro = client.post("/api/v1/diario/interpretar", headers=otro_headers, json=texto).json()
    assert otro["items"][0]["origen"] == "sin_estimar"


def test_receta_guarda_pasos_para_modo_cocina():
    headers, _ = _registrar_usuario()
    res = client.post("/api/v1/recetas", headers=headers, json={
        "nombre": "Arroz test", "calorias_totales": 300, "proteinas_totales": 6,
        "carbohidratos_totales": 60, "grasas_totales": 1, "pasos": ["Hervir 20 min", "Escurrir"]
    })
    assert res.status_code == 200, res.text
    recetas = client.get("/api/v1/recetas", headers=headers).json()
    assert recetas[0]["pasos"] == ["Hervir 20 min", "Escurrir"]
