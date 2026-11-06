"""Tren de tratamiento de lodos: espesamiento, digestión y deshidratación.

Los balances son másicos (kg/d de sólidos) y de caudal (m3/d). Se asume
régimen permanente y mezcla completa en cada unidad. Las corrientes de
rechazo (sobrenadante del espesador y filtrado del deshidratador) se
recirculan a la cabecera de la planta.

Referencias
-----------
    Metcalf & Eddy, AECOM (2014). Wastewater Engineering, 5th ed.
    von Sperling, M. (2007). Wastewater Characteristics, Treatment and
        Disposal. IWA Publishing.
"""

from __future__ import annotations

import math

from . import constants as K


def tren_lodos(
    lodo_primario_m3_d: float,
    solidos_primario_kg_d: float,
    purga_m3_d: float,
    sst_purga_mg_l: float,
    caudal_planta_m3_d: float,
    carga_dqo_removida_kg_d: float | None = None,
    captura_espesador: float = 0.90,
    captura_deshidratacion: float = 0.95,
) -> dict:
    """Balance del tren de lodos.

    Parámetros
    ----------
    lodo_primario_m3_d : caudal de lodo primario
    solidos_primario_kg_d : sólidos secos del lodo primario
    purga_m3_d : caudal de purga del sedimentador secundario
    sst_purga_mg_l : concentración de sólidos de la purga
    caudal_planta_m3_d : caudal de agua tratada (referencia para cargas)
    """
    q_prim = max(lodo_primario_m3_d, 0.0)
    s_prim = max(solidos_primario_kg_d, 0.0)
    q_purga = max(purga_m3_d, 0.0)
    s_purga = q_purga * max(sst_purga_mg_l, 0.0) / 1000.0

    # ------------------------------------------------------------------
    # 1. Espesador por gravedad
    # ------------------------------------------------------------------
    q_esp_in = q_prim + q_purga
    s_esp_in = s_prim + s_purga
    s_esp_sub = captura_espesador * s_esp_in
    s_esp_rech = s_esp_in - s_esp_sub
    q_esp_sub = s_esp_sub / (K.SOLIDOS_ESPESADO * 1000.0)
    q_esp_rech = max(q_esp_in - q_esp_sub, 0.0)
    carga_esp = s_esp_in / max(0.5 * math.pi * 6.0 ** 2, 1e-9)   # kg/(m2·d) aprox.

    # ------------------------------------------------------------------
    # 2. Digestor anaerobio
    # ------------------------------------------------------------------
    s_dig_in = s_esp_sub
    vs_dig_in = 0.75 * s_dig_in                    # 75 % de SST son volátiles
    vs_destruido = K.VS_DESTRUIDO * vs_dig_in
    s_dig_out = s_dig_in - vs_destruido
    q_dig_out = s_dig_out / (0.035 * 1000.0)       # 3,5 % SST a la salida
    trh_dias = 20.0
    v_digestor = max(q_esp_sub * trh_dias, 100.0)
    biogas_m3_d = K.BIOGAS_POR_VS * vs_destruido
    metano_m3_d = K.CH4_FRACCION * biogas_m3_d
    energia_mj_d = metano_m3_d * K.PODER_CAL_CH4
    energia_kwh_d = energia_mj_d * K.EFICIENCIA_ELECTRICA_CHP / 3.6
    energia_termica_kwh_d = energia_mj_d * K.EFICIENCIA_TERMICA_CHP / 3.6
    # 1 kg COD ≈ 0,35 m3 CH4 a condiciones normales
    cod_destruido_kg_d = metano_m3_d / 0.35

    # ------------------------------------------------------------------
    # 3. Deshidratación (centrífuga / banda)
    # ------------------------------------------------------------------
    s_torta = captura_deshidratacion * s_dig_out
    s_filtrado = s_dig_out - s_torta
    q_torta = s_torta / (K.SOLIDOS_TORTA * 1000.0)
    q_filtrado = max(q_dig_out - q_torta, 0.0)
    camiones_dia = q_torta / 12.0                   # camión de 12 m3

    # ------------------------------------------------------------------
    # 4. Recirculación interna de rechazos a cabecera
    # ------------------------------------------------------------------
    q_rechazo = q_esp_rech + q_filtrado
    s_rechazo = s_esp_rech + s_filtrado
    recirculacion_pct = 100.0 * q_rechazo / max(caudal_planta_m3_d, 1e-9)
    # Carga adicional que vuelve a entrar al tren de agua
    carga_adicional_dbo = 0.35 * s_rechazo * 1000.0 / max(q_rechazo, 1e-9)
    carga_adicional_sst = 1000.0 * s_rechazo / max(q_rechazo, 1e-9)

    etapas = [
        {
            "id": "espesador",
            "nombre": "Espesador de lodos",
            "detalle": "Gravedad, captura 90 %",
            "entrada_m3_d": round(q_esp_in, 1),
            "entrada_kg_sst_d": round(s_esp_in, 1),
            "salida_m3_d": round(q_esp_sub, 1),
            "salida_kg_sst_d": round(s_esp_sub, 1),
            "concentracion_pct": round(100.0 * K.SOLIDOS_ESPESADO, 2),
            "rechazo_m3_d": round(q_esp_rech, 1),
            "rechazo_kg_sst_d": round(s_esp_rech, 1),
            "carga_kg_m2_d": round(carga_esp, 1),
        },
        {
            "id": "digestor",
            "nombre": "Digestor anaerobio",
            "detalle": f"TRH {trh_dias:.0f} d, 35 °C",
            "entrada_m3_d": round(q_esp_sub, 1),
            "entrada_kg_sst_d": round(s_dig_in, 1),
            "salida_m3_d": round(q_dig_out, 1),
            "salida_kg_sst_d": round(s_dig_out, 1),
            "volumen_m3": round(v_digestor, 0),
            "vs_destruido_kg_d": round(vs_destruido, 1),
            "biogas_m3_d": round(biogas_m3_d, 0),
            "metano_m3_d": round(metano_m3_d, 0),
            "energia_kwh_d": round(energia_kwh_d, 0),
            "energia_termica_kwh_d": round(energia_termica_kwh_d, 0),
        },
        {
            "id": "deshidratacion",
            "nombre": "Deshidratación",
            "detalle": "Centrífuga, torta 22 % SST",
            "entrada_m3_d": round(q_dig_out, 1),
            "entrada_kg_sst_d": round(s_dig_out, 1),
            "torta_m3_d": round(q_torta, 1),
            "torta_kg_sst_d": round(s_torta, 1),
            "filtrado_m3_d": round(q_filtrado, 1),
            "filtrado_kg_sst_d": round(s_filtrado, 1),
            "camiones_dia": round(camiones_dia, 1),
        },
    ]

    return {
        "etapas": etapas,
        "resumen": {
            "lodo_primario_m3_d": round(q_prim, 1),
            "lodo_primario_kg_sst_d": round(s_prim, 1),
            "purga_m3_d": round(q_purga, 1),
            "purga_kg_sst_d": round(s_purga, 1),
            "solidos_entrada_kg_d": round(s_esp_in, 1),
            "concentracion_entrada_pct": round(s_esp_in / max(q_esp_in, 1e-9) / 10.0, 2),
            "torta_m3_d": round(q_torta, 1),
            "torta_kg_sst_d": round(s_torta, 1),
            "biogas_m3_d": round(biogas_m3_d, 0),
            "metano_m3_d": round(metano_m3_d, 0),
            "energia_kwh_d": round(energia_kwh_d, 0),
            "energia_termica_kwh_d": round(energia_termica_kwh_d, 0),
            "energia_kwh_por_m3": round(energia_kwh_d / max(caudal_planta_m3_d, 1.0), 3),
            "cod_destruido_kg_d": round(cod_destruido_kg_d, 1),
            "recirculacion_m3_d": round(q_rechazo, 1),
            "recirculacion_pct": round(recirculacion_pct, 2),
            "rechazo_sst_mg_l": round(carga_adicional_sst, 0),
            "rechazo_dbo5_mg_l": round(carga_adicional_dbo, 0),
            "produccion_especifica_kg_sst_kg_dqo": round(
                s_torta / max(carga_dqo_removida_kg_d or caudal_planta_m3_d, 1e-9), 4
            ),
        },
    }
