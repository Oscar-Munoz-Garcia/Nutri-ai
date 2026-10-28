import uuid
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.services.metabolic_service import regresion_lineal, calcular_tdee, puntuar_dia

client = TestClient(app)


def _fecha(dias_atras: int) -> str:
    return (date.today() - timedelta(days=dias_atras)).isoformat()


def test_regresion_lineal_recta_perfecta():
    pendiente, intercepto, r2 = regresion_lineal([0, 1, 2, 3], [80.0, 79.9, 79.8, 79.7])
    assert round(pendiente, 3) == -0.1
    assert round(intercepto, 2) == 80.0
    assert round(r2, 3) == 1.0


def test_tdee_deficit_conocido():
    # 2000 kcal/día y se pierde 0.5 kg/semana -> TDEE ≈ 2000 + 0.5/7 * 7700 = 2550
    ingestas = {_fecha(i): 2000.0 for i in range(21)}
    pesajes = [(_fecha(21 - d), 80.0 - 0.5 * d / 7) for d in (0, 3, 7, 10, 14, 17, 21)]
    resultado = calcular_tdee(ingestas, pesajes)
    assert resultado is not None
    assert abs(resultado["tdee"] - 2550) < 1


def test_tdee_ignora_dias_sin_registro_y_exige_datos():
    ingestas = {_fecha(i): (2500.0 if i % 2 == 0 else 0.0) for i in range(28)}
    pesajes = [(_fecha(27), 80.0), (_fecha(14), 80.0), (_fecha(0), 80.0)]
    resultado = calcular_tdee(ingestas, pesajes)
    assert round(resultado["tdee"]) == 2500
    # Solo dos pesajes -> insuficiente
    assert calcular_tdee(ingestas, pesajes[:2]) is None
    # Pesajes demasiado juntos -> insuficiente
    assert calcular_tdee(ingestas, [(_fecha(2), 80.0), (_fecha(1), 80.1), (_fecha(0), 80.0)]) is None


def test_puntuar_dia():
    assert puntuar_dia(2200, 160, 2200, 160) == 1.0
    assert puntuar_dia(0, 0, 2200, 160) == 0.0
    # 20% por encima en calorías -> 50% de nota calórica, proteína completa
    assert round(puntuar_dia(2640, 160, 2200, 160), 2) == 0.75
    # Calorías perfectas, mitad de proteína
    assert puntuar_dia(2200, 80, 2200, 160) == 0.75


def test_endpoints_peso_y_tdee():
    res = client.post("/api/v1/peso", json={"peso_kg": 77.4, "fecha": _fecha(0)})
    assert res.status_code == 200
    peso_id = res.json()["id"]

    # Mismo día: se sobrescribe en lugar de duplicar
    res = client.post("/api/v1/peso", json={"peso_kg": 77.2, "fecha": _fecha(0)})
    assert res.json()["id"] == peso_id
    assert res.json()["peso_kg"] == 77.2

    pesos = client.get("/api/v1/peso").json()
    assert sum(1 for p in pesos if p["fecha"] == _fecha(0)) == 1

    tdee = client.get("/api/v1/metabolismo/tdee").json()
    assert tdee["estado"] in ("ok", "insuficiente")
    assert tdee["tdee_teorico"] > 0

    assert client.post("/api/v1/peso", json={"peso_kg": 77.0, "fecha": "no-es-fecha"}).status_code == 422
    assert client.delete(f"/api/v1/peso/{peso_id}").status_code == 200
    assert client.delete(f"/api/v1/peso/{peso_id}").status_code == 404


def test_endpoint_versus():
    # Un segundo participante con su propio token
    nombre = f"rival_{uuid.uuid4().hex[:8]}"
    token = client.post("/api/v1/auth/registro", json={
        "username": nombre, "email": f"{nombre}@nutri.ai", "password": "secreta123"
    }).json()["access_token"]
    rival = client.get("/api/v1/versus", headers={"Authorization": f"Bearer {token}"}).json()
    yo_rival = next(p for p in rival["participantes"] if p["es_yo"])
    assert yo_rival["nombre"] == nombre
    assert yo_rival["porcentaje_semana"] == 0.0

    res = client.get("/api/v1/versus")
    assert res.status_code == 200
    data = res.json()
    assert date.fromisoformat(data["semana_inicio"]).weekday() == 0
    assert any(p["es_yo"] for p in data["participantes"])
    for p in data["participantes"]:
        assert 0 <= p["porcentaje_semana"] <= 100
        if not p["es_yo"]:
            assert all(d["calorias"] is None for d in p["dias"])


def test_pesos_aislados_por_usuario():
    def token_nuevo():
        nombre = f"user_{uuid.uuid4().hex[:8]}"
        return {"Authorization": "Bearer " + client.post("/api/v1/auth/registro", json={
            "username": nombre, "email": f"{nombre}@nutri.ai", "password": "secreta123"
        }).json()["access_token"]}

    a, b = token_nuevo(), token_nuevo()
    peso_id = client.post("/api/v1/peso", json={"peso_kg": 70.0}, headers=a).json()["id"]
    assert client.get("/api/v1/peso", headers=b).json() == []
    assert client.delete(f"/api/v1/peso/{peso_id}", headers=b).status_code == 404
    assert len(client.get("/api/v1/peso", headers=a).json()) == 1


def _usuario_nuevo():
    nombre = f"amigo_{uuid.uuid4().hex[:8]}"
    token = client.post("/api/v1/auth/registro", json={
        "username": nombre, "email": f"{nombre}@nutri.ai", "password": "secreta123"
    }).json()["access_token"]
    return nombre, {"Authorization": f"Bearer {token}"}


def _ids_versus(headers):
    return {p["nombre"] for p in client.get("/api/v1/versus", headers=headers).json()["participantes"]}


def test_versus_solo_entre_amigos():
    (a, ha), (b, hb), (c, hc) = _usuario_nuevo(), _usuario_nuevo(), _usuario_nuevo()

    # Sin amigos, solo apareces tú
    assert _ids_versus(ha) == {a}

    # A envía solicitud a B: pendiente, B aún no aparece
    assert client.post("/api/v1/amigos/solicitudes", json={"usuario": b}, headers=ha).json()["status"] == "enviada"
    assert client.post("/api/v1/amigos/solicitudes", json={"usuario": b}, headers=ha).status_code == 400
    assert _ids_versus(ha) == {a}
    recibidas = client.get("/api/v1/amigos", headers=hb).json()["recibidas"]
    assert [r["usuario"]["username"] for r in recibidas] == [a]

    # Solo el destinatario puede aceptar
    assert client.post(f"/api/v1/amigos/solicitudes/{recibidas[0]['id']}/aceptar", headers=ha).status_code == 404
    assert client.post(f"/api/v1/amigos/solicitudes/{recibidas[0]['id']}/aceptar", headers=hb).status_code == 200
    assert _ids_versus(ha) == {a, b}
    assert _ids_versus(hb) == {a, b}
    assert c not in _ids_versus(ha)

    # Del amigo no se ven calorías ni proteínas
    for p in client.get("/api/v1/versus", headers=ha).json()["participantes"]:
        if not p["es_yo"]:
            assert all(d["calorias"] is None and d["proteinas"] is None for d in p["dias"])

    # C rechaza la solicitud de A
    client.post("/api/v1/amigos/solicitudes", json={"usuario": c}, headers=ha)
    sol_id = client.get("/api/v1/amigos", headers=hc).json()["recibidas"][0]["id"]
    assert client.delete(f"/api/v1/amigos/solicitudes/{sol_id}", headers=hc).status_code == 200
    assert client.get("/api/v1/amigos", headers=ha).json()["enviadas"] == []

    # Si C envía a B y B envía a C, se aceptan sin más pasos
    client.post("/api/v1/amigos/solicitudes", json={"usuario": b}, headers=hc)
    assert client.post("/api/v1/amigos/solicitudes", json={"usuario": c}, headers=hb).json()["status"] == "aceptada"
    assert _ids_versus(hb) == {a, b, c}

    # Eliminar amistad
    b_id = client.get("/api/v1/amigos", headers=ha).json()["amigos"][0]["usuario_id"]
    assert client.delete(f"/api/v1/amigos/{b_id}", headers=ha).status_code == 200
    assert _ids_versus(ha) == {a}

    # Errores
    assert client.post("/api/v1/amigos/solicitudes", json={"usuario": a}, headers=ha).status_code == 400
    assert client.post("/api/v1/amigos/solicitudes", json={"usuario": "no_existe_xyz"}, headers=ha).status_code == 404
