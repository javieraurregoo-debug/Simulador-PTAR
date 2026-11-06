import json

import pytest

from app.simulation.plant import preset, simular_desde_parametros


@pytest.fixture(scope="module")
def resultado_municipal():
    return simular_desde_parametros(preset("municipal"))


def test_simulacion_es_serializable(resultado_municipal):
    texto = json.dumps(resultado_municipal, ensure_ascii=False)
    assert len(texto) > 1000
    assert "kpis" in resultado_municipal


def test_remocion_de_contaminantes(resultado_municipal):
    kpis = resultado_municipal["kpis"]
    assert kpis["dbo5"]["eficiencia_pct"] > 90
    assert kpis["dqo"]["eficiencia_pct"] > 85
    assert kpis["sst"]["eficiencia_pct"] > 90
    assert kpis["nt"]["eficiencia_pct"] > 60
    assert 0 < kpis["tp"]["eficiencia_pct"] < 60


def test_efluente_es_menor_que_afluente(resultado_municipal):
    afluente = resultado_municipal["afluente"]
    efluente = resultado_municipal["efluente"]
    for clave in ("dbo5_mg_l", "dqo_mg_l", "sst_mg_l", "nt_mg_l"):
        assert efluente[clave] < afluente[clave]


def test_cierre_de_balances(resultado_municipal):
    balance = resultado_municipal["balance"]
    assert 85 <= balance["sst"]["cierre_pct"] <= 115
    assert 85 <= balance["dqo"]["cierre_pct"] <= 115


def test_operacion_biologica_coherente(resultado_municipal):
    op = resultado_municipal["operacion_biologica"]
    assert 5 < op["srt_d"] < 40
    assert 0.03 < op["fm_kg_cod_kg_ssv_d"] < 0.5
    assert 1000 < op["mlss_mg_l"] < 6000
    assert op["our_kg_o2_d"] > 0
    assert op["aire_m3_d"] > 0


def test_tren_de_lodos(resultado_municipal):
    resumen = resultado_municipal["tren_lodos"]["resumen"]
    assert resumen["torta_kg_sst_d"] > 0
    assert resumen["biogas_m3_d"] > 0
    assert resumen["energia_kwh_d"] > 0
    assert 0 < resumen["concentracion_entrada_pct"] < 10


def test_perfil_contiene_todas_las_etapas(resultado_municipal):
    assert len(resultado_municipal["perfil"]) == len(resultado_municipal["etapas"]) + 1
    nombres = [p["etapa"] for p in resultado_municipal["perfil"]]
    assert nombres[0] == "Afluente"
    assert "Desinfección" in nombres


def test_tiempo_de_calculo(resultado_municipal):
    assert resultado_municipal["meta"]["duracion_ms"] < 60000
