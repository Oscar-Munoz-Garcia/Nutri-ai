from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_perfil_separado_de_los_planes():
    html = client.get("/").text
    # La cabecera abre el perfil y ya no enlaza a la documentación de la API
    assert 'id="btn-perfil-cabecera"' in html
    assert 'href="/docs"' not in html
    assert "05 / Planes" in html
    planes = html[html.index('id="sec-perfil"'):html.index('id="sec-cuenta"')]
    cuenta = html[html.index('id="sec-cuenta"'):html.index('id="sec-versus"')]
    # Los datos personales viven en el perfil; los objetivos y planes siguen en Planes
    for campo in ('id="prof-nombre"', 'id="prof-edad"', 'id="prof-peso"', 'id="prof-altura"'):
        assert campo in cuenta and campo not in planes
    for campo in ('id="prof-modo"', 'id="prof-dias-libres"', 'id="bloque-planes"'):
        assert campo in planes
    # Cerrar sesión y, debajo, eliminar cuenta
    assert cuenta.index("Cerrar sesión") < cuenta.index("Eliminar mi cuenta")
    assert "Este botón elimina tu cuenta." in cuenta


def test_textos_del_perfil_traducidos():
    i18n = client.get("/static/i18n.js").text
    for texto in ("Cerrar sesión", "05 / Planes", "Datos personales", "Guardar datos",
                  "¿Seguro que quieres eliminar tu cuenta?", "¿Continuar con la eliminación?"):
        assert f'"{texto}"' in i18n
