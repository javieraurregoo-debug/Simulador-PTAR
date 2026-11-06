import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.simulation.plant import preset

cliente = TestClient(app)


@pytest.fixture(scope="module")
def simulacion():
    respuesta = cliente.post("/api/simulaciones", json=preset("municipal"))
    assert respuesta.status_code == 200, respuesta.text
    return respuesta


def test_salud():
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"


def test_catalogo():
    respuesta = cliente.get("/api/catalogo")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert len(datos["unidades"]) == 13
    assert len(datos["ecuaciones"]) >= 8
    assert len(datos["presets"]) == 4
    ids = {u["id"] for u in datos["unidades"]}
    assert {"rejillas", "primario", "aerobio", "secundario", "digestor"} <= ids


def test_presets():
    lista = cliente.get("/api/presets").json()
    assert {p["id"] for p in lista} == {"municipal", "municipal_lluvia", "industrial", "pequena"}
    detalle = cliente.get("/api/presets/industrial")
    assert detalle.status_code == 200
    assert detalle.json()["influente"]["dqo_mg_l"] == 1500


def test_preset_inexistente():
    assert cliente.get("/api/presets/inexistente").status_code == 404


def test_simulacion_y_cache(simulacion):
    datos = simulacion.json()
    assert datos["kpis"]["dbo5"]["eficiencia_pct"] > 90
    assert datos["efluente"]["sst_mg_l"] < 30
    assert simulacion.headers["X-Simulation-Cache"] == "MISS"

    repetida = cliente.post("/api/simulaciones", json=preset("municipal"))
    assert repetida.status_code == 200
    assert repetida.headers["X-Simulation-Cache"] == "HIT"


def test_validacion_dbo_mayor_que_dqo():
    peticion = preset("municipal")
    peticion["influente"]["dbo5_mg_l"] = 900
    peticion["influente"]["dqo_mg_l"] = 500
    respuesta = cliente.post("/api/simulaciones", json=peticion)
    assert respuesta.status_code == 422


def test_validacion_campo_extra():
    peticion = preset("municipal")
    peticion["influente"]["campo_inventado"] = 1
    respuesta = cliente.post("/api/simulaciones", json=peticion)
    assert respuesta.status_code == 422


def test_ecuaciones():
    respuesta = cliente.get("/api/ecuaciones")
    assert respuesta.status_code == 200
    ids = {e["id"] for e in respuesta.json()}
    assert {"dqo", "dbo5", "sst", "srt", "vesilind"} <= ids


def test_metodo_de_desinfeccion_invalido():
    peticion = preset("municipal")
    peticion["diseno"]["desinfeccion"]["metodo"] = "plasma"
    respuesta = cliente.post("/api/simulaciones", json=peticion)
    assert respuesta.status_code == 422
