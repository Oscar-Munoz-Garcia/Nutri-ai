from fastapi.testclient import TestClient
from app.main import app

from tests.usuarios import crear_usuario

client = TestClient(app)


def _cab(token):
    return {"Authorization": f"Bearer {token}"}


def test_macros_exactos_cuadran_con_las_calorias_del_formulario():
    # 2400 kcal con 190 g de proteína y 230 g de carbos dejan 80 g de grasas
    cab = _cab(crear_usuario("macros_exactos"))
    r = client.put("/api/v1/perfil", headers=cab, json={
        "modo_objetivo": "manual_macros", "proteinas_g": 190, "carbohidratos_g": 230, "grasas_g": 80})
    assert r.status_code == 200
    obj = r.json()["objetivos_diarios"]
    assert obj["calorias_objetivo"] == 2400
    assert obj["grasas_objetivo"] == 80


def test_pantalla_perfil_trae_campo_kcal_y_aviso_de_plan_principal():
    html = client.get("/").text
    for marca in ('id="prof-kcal-exactas"', 'id="aviso-kcal-exactas"', 'id="modalPlanPrincipal"',
                  "Esto actualiza solo el plan principal, puedes crear más planes en 'Tus Planes'."):
        assert marca in html
    i18n = client.get("/static/i18n.js").text
    assert "Esto actualiza solo el plan principal, puedes crear más planes en 'Tus Planes'." in i18n
