import math

from app.simulation.quality import (
    comprobar_limites,
    eficiencia,
    fraccionar_influente,
    indice_calidad_agua,
)
from app.simulation.streams import Stream


def test_fraccionamiento_cierra_el_balance_de_dqo():
    s, meta = fraccionar_influente(
        caudal_m3_d=9000,
        dbo5_mg_l=240,
        dqo_mg_l=455,
        sst_mg_l=230,
        ssv_mg_l=185,
        ntk_mg_l=42,
        nh4_mg_l=32,
        pt_mg_l=7,
        po4_mg_l=5,
    )
    fracciones = meta["fracciones_cod"]
    suma = sum(fracciones.values())
    assert math.isclose(suma, 455.0, rel_tol=1e-6)
    assert math.isclose(s.cod, 455.0, rel_tol=1e-6)
    assert math.isclose(s.bod5, 240.0, abs_tol=0.2)
    assert s.tss == 230.0
    assert s.tkn >= 42.0 - 1e-6
    assert not meta["advertencias"]


def test_fraccionamiento_ajusta_dbo_incoherente():
    s, meta = fraccionar_influente(
        caudal_m3_d=1000,
        dbo5_mg_l=900,
        dqo_mg_l=500,
        sst_mg_l=300,
    )
    assert s.bod5 <= 0.65 * 500 + 1e-6
    assert any("DBO5" in a or "DBO" in a for a in meta["advertencias"])


def test_eficiencia_masica():
    entrada = Stream(q=100, ss=100, tss=100)
    salida = Stream(q=100, ss=10, tss=20)
    assert math.isclose(eficiencia(entrada, salida, "dbo5"), 90.0, abs_tol=1e-6)
    assert math.isclose(eficiencia(entrada, salida, "sst"), 80.0, abs_tol=1e-6)


def test_limites_e_indice():
    salida = Stream(q=100, ss=5, tss=10, nh4=1, sno=2, spo4=0.5, coliforms=100)
    limites = comprobar_limites(salida)
    assert limites["dbo5_mg_l"]["cumple"] is True
    assert limites["cumple_global"] is True
    indice = indice_calidad_agua(salida)
    assert 0 <= indice["valor"] <= 100
    assert indice["clasificacion"] in {"Excelente", "Buena", "Aceptable", "Deficiente"}
