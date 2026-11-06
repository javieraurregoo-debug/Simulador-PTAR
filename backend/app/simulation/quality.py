"""Caracterización y fraccionamiento de la materia orgánica.

El modelo trabaja con las fracciones de COD de ASM1 (S_I, S_S, X_S, X_I,
X_BH, X_BA). El usuario, en cambio, caracteriza el agua residual con los
parámetros convencionales DBO5, DQO y SST. Este módulo traduce ambas
representaciones de forma consistente:

    DQO   = S_I + S_S + X_S + X_I + X_BH + X_BA          [g COD/m3]
    DBO5  = f_BOD * (S_S + X_S + X_BH + X_BA)            [g O2/m3]
    SST   = ISS + (X_S + X_I + X_BH + X_BA) / i_COD_SST  [g SST/m3]

con f_BOD = 0,65 g DBO5/g COD biodegradable e i_COD_SST = 1,14 g COD/g SST,
valores de compromiso para agua residual municipal (Metcalf & Eddy, 2014;
von Sperling, 2007).

Referencias
-----------
    Metcalf & Eddy, AECOM (2014). Wastewater Engineering: Treatment and
        Resource Recovery, 5th ed. McGraw-Hill.
    von Sperling, M. (2007). Activated Sludge and Aerobic Biofilm Reactors.
        IWA Publishing.
    Henze, M. et al. (1987). Activated Sludge Model No. 1. IAWPRC.
"""

from __future__ import annotations

import math

from .streams import Stream, normalizar_concentraciones

F_BOD = 0.65          # g DBO5 / g COD biodegradable
I_COD_SST = 1.14      # g COD / g SST
I_VSS_SST = 0.82      # g SSV / g SST (agua residual municipal)
I_N_XS = 0.05         # g N / g COD en X_S
I_N_XI = 0.06         # g N / g COD en X_I
I_N_S = 0.02          # g N / g COD en S_I y S_S

# Rangos típicos de agua residual municipal (solo para advertencias)
RANGOS = {
    "dbo5": (100.0, 500.0),
    "dqo": (200.0, 1000.0),
    "sst": (100.0, 500.0),
    "dqo_dbo5": (1.5, 2.8),
    "ssv_sst": (0.65, 0.90),
    "ph": (6.0, 8.5),
}


def _clip(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def fraccionar_influente(
    caudal_m3_d: float,
    dbo5_mg_l: float,
    dqo_mg_l: float,
    sst_mg_l: float,
    ssv_mg_l: float | None = None,
    ntk_mg_l: float | None = None,
    nh4_mg_l: float | None = None,
    no3_mg_l: float = 0.0,
    pt_mg_l: float | None = None,
    po4_mg_l: float | None = None,
    alcalinidad_mg_l: float = 250.0,
    ph: float = 7.2,
    temperatura_c: float = 20.0,
    coliformes_ufc_100ml: float = 1.0e7,
    turbiedad_ntu: float = 150.0,
    si_frac: float = 0.06,
    ssv_frac: float = I_VSS_SST,
) -> tuple[Stream, dict]:
    """Convierte DBO5, DQO y SST en las fracciones de COD del modelo.

    Estrategia de reparto
    ---------------------
    1. El COD soluble inerte se fija como una fracción (6 % por defecto) del
       DQO; es la fracción que atraviesa el tren biológico sin transformarse.
    2. El COD biodegradable objetivo se obtiene de la DBO5:
       ``bCOD = DBO5 / 0,65``. Se acota para que nunca exceda el DQO.
    3. El COD inerte particulado cierra el balance de DQO:
       ``X_I = DQO - S_I - bCOD``.
    4. El bCOD se reparte entre S_S y X_S usando los SSV medidos
       (COD particulado ≈ 1,42 · SSV). El resto es sustrato soluble.

    Devuelve la corriente y un diccionario con los indicadores de calidad y
    las advertencias de consistencia.
    """
    advertencias: list[str] = []

    q = max(float(caudal_m3_d), 1.0)
    dbo5 = max(float(dbo5_mg_l), 0.0)
    dqo = max(float(dqo_mg_l), 1.0)
    sst = max(float(sst_mg_l), 0.0)
    ssv = float(ssv_mg_l) if ssv_mg_l is not None else ssv_frac * sst

    if dbo5 >= dqo:
        advertencias.append(
            "DBO5 ≥ DQO: se ajustó la DBO5 al 65 % de la DQO para mantener "
            "la consistencia fisicoquímica."
        )
        dbo5 = 0.65 * dqo
    if dbo5 > 0.70 * dqo:
        advertencias.append(
            "La relación DBO5/DQO es superior a 0,70; se acotó el COD "
            "biodegradable para evitar fracciones negativas."
        )
        dbo5 = 0.65 * dqo
    if ssv > sst:
        advertencias.append("SSV > SST: se igualaron los SSV a los SST.")
        ssv = sst

    # ---- Reparto del COD -------------------------------------------------
    si = si_frac * dqo
    bcod_objetivo = dbo5 / F_BOD
    bcod_max = 0.94 * dqo - si
    bcod = _clip(bcod_objetivo, 0.20 * dqo, max(0.20 * dqo, bcod_max))
    xi = max(dqo - si - bcod, 0.0)

    # COD particulado medido a partir de SSV: 1,42 g COD/g SSV
    particulado_medido = 1.42 * ssv - xi
    xs_objetivo = _clip(particulado_medido, 0.15 * bcod, 0.90 * bcod)
    xs = xs_objetivo
    ss = max(bcod - xs, 0.0)

    # ---- Nitrógeno -------------------------------------------------------
    organico_n = xs * I_N_XS + xi * I_N_XI + ss * I_N_S + si * I_N_S
    if nh4_mg_l is not None:
        nh4 = max(float(nh4_mg_l), 0.0)
        if ntk_mg_l is not None and ntk_mg_l < nh4:
            advertencias.append("NTK < N-NH4: se usó el amonio como N total.")
    elif ntk_mg_l is not None:
        nh4 = max(float(ntk_mg_l) - organico_n, 0.2)
    else:
        nh4 = 0.75 * 42.0        # valor de referencia municipal
        advertencias.append(
            "Sin datos de nitrógeno: se asumió una concentración de amonio "
            "de 31,5 mg N/L."
        )

    # ---- Fósforo ---------------------------------------------------------
    if po4_mg_l is not None:
        po4 = max(float(po4_mg_l), 0.0)
    elif pt_mg_l is not None:
        po4 = max(float(pt_mg_l), 0.0)
    else:
        po4 = 6.0
        advertencias.append("Sin datos de fósforo: se asumieron 6,0 mg P/L.")

    corriente = Stream(
        q=q,
        si=si,
        ss=ss,
        xs=xs,
        xi=xi,
        xbh=0.0,
        xba=0.0,
        tss=sst,
        vss=min(ssv, sst),
        nh4=nh4,
        sno=max(float(no3_mg_l), 0.0),
        spo4=po4,
        xpp=0.0,
        alk=max(float(alcalinidad_mg_l), 5.0),
        ph=_clip(float(ph), 4.0, 10.0),
        temp=float(temperatura_c),
        coliforms=max(float(coliformes_ufc_100ml), 1.0),
        turbidity=max(float(turbiedad_ntu), 0.1),
    )
    normalizar_concentraciones(corriente)

    relacion_dqo_dbo = dqo / max(dbo5, 1e-9)
    relacion_ssv_sst = corriente.vss / max(sst, 1e-9)
    cod_particulado = xs + xi
    relacion_cod_sst = cod_particulado / max(sst, 1e-9)

    if not (RANGOS["dqo_dbo5"][0] <= relacion_dqo_dbo <= RANGOS["dqo_dbo5"][1]):
        advertencias.append(
            f"DQO/DBO5 = {relacion_dqo_dbo:.2f}, fuera del rango típico "
            f"{RANGOS['dqo_dbo5'][0]:.1f}–{RANGOS['dqo_dbo5'][1]:.1f}."
        )
    if sst > 0 and not (RANGOS["ssv_sst"][0] <= relacion_ssv_sst <= RANGOS["ssv_sst"][1]):
        advertencias.append(
            f"SSV/SST = {relacion_ssv_sst:.2f}, fuera del rango típico "
            f"{RANGOS['ssv_sst'][0]:.2f}–{RANGOS['ssv_sst'][1]:.2f}."
        )
    if not (RANGOS["ph"][0] <= corriente.ph <= RANGOS["ph"][1]):
        advertencias.append(
            f"pH = {corriente.ph:.2f}, fuera del rango habitual de un agua "
            "residual municipal (6,0–8,5)."
        )
    if not (0.5 <= relacion_cod_sst <= 2.2):
        advertencias.append(
            f"COD particulado/SST = {relacion_cod_sst:.2f}; revise la "
            "coherencia entre DQO y SST."
        )

    meta = {
        "caudal_m3_d": round(corriente.q, 1),
        "carga_dbo5_kg_d": round(corriente.bod5 * corriente.q / 1000.0, 1),
        "carga_dqo_kg_d": round(corriente.cod * corriente.q / 1000.0, 1),
        "carga_sst_kg_d": round(corriente.tss * corriente.q / 1000.0, 1),
        "dbo5_modelo_mg_l": round(corriente.bod5, 1),
        "dqo_modelo_mg_l": round(corriente.cod, 1),
        "sst_modelo_mg_l": round(corriente.tss, 1),
        "relacion_dqo_dbo5": round(relacion_dqo_dbo, 2),
        "relacion_ssv_sst": round(relacion_ssv_sst, 2),
        "relacion_cod_sst": round(relacion_cod_sst, 2),
        "fracciones_cod": {
            "si": round(si, 1),
            "ss": round(ss, 1),
            "xs": round(xs, 1),
            "xi": round(xi, 1),
            "xbh": 0.0,
            "xba": 0.0,
        },
        "advertencias": advertencias,
    }
    return corriente, meta


def resumen_calidad(s: Stream) -> dict:
    """Indicadores convencionales de una corriente (tipos nativos)."""

    def r(valor: float, n: int = 1) -> float:
        return round(float(valor), n)

    return {
        "caudal_m3_d": r(s.q),
        "dqo_mg_l": r(s.cod),
        "dbo5_mg_l": r(s.bod5),
        "sst_mg_l": r(s.tss),
        "ssv_mg_l": r(s.vss),
        "ntk_mg_l": r(s.tkn),
        "n_nh4_mg_l": r(s.nh4),
        "n_no3_mg_l": r(s.sno),
        "nt_mg_l": r(s.tn),
        "pt_mg_l": r(s.tp, 2),
        "p_po4_mg_l": r(s.spo4, 2),
        "ph": r(s.ph, 2),
        "alcalinidad_mg_l": r(s.alk),
        "temperatura_c": r(s.temp),
        "coliformes_ufc_100ml": r(s.coliforms, 0),
        "turbiedad_ntu": r(s.turbidity),
        "carga_dqo_kg_d": r(s.cod * s.q / 1000.0),
        "carga_dbo5_kg_d": r(s.bod5 * s.q / 1000.0),
        "carga_sst_kg_d": r(s.tss * s.q / 1000.0),
    }


def eficiencia(entrada: Stream, salida: Stream, parametro: str) -> float:
    """Eficiencia de remoción másica (%) de un parámetro."""
    if parametro == "dbo5":
        carga_in = entrada.bod5 * entrada.q
        carga_out = salida.bod5 * salida.q
    elif parametro == "dqo":
        carga_in = entrada.cod * entrada.q
        carga_out = salida.cod * salida.q
    elif parametro == "sst":
        carga_in = entrada.tss * entrada.q
        carga_out = salida.tss * salida.q
    elif parametro == "nt":
        carga_in = entrada.tn * entrada.q
        carga_out = salida.tn * salida.q
    elif parametro == "tp":
        carga_in = entrada.tp * entrada.q
        carga_out = salida.tp * salida.q
    else:
        return 0.0
    if carga_in <= 1e-9:
        return 0.0
    return max(0.0, min(100.0, 100.0 * (1.0 - carga_out / carga_in)))


def comprobar_limites(salida: Stream, limites: dict | None = None) -> dict:
    """Compara el efluente con límites de referencia configurables."""
    limites = limites or {
        "dbo5_mg_l": 50.0,
        "dqo_mg_l": 150.0,
        "sst_mg_l": 50.0,
        "nt_mg_l": 15.0,
        "pt_mg_l": 2.0,
        "ph_min": 6.0,
        "ph_max": 9.0,
        "coliformes_ufc_100ml": 1000.0,
    }
    valores = {
        "dbo5_mg_l": salida.bod5,
        "dqo_mg_l": salida.cod,
        "sst_mg_l": salida.tss,
        "nt_mg_l": salida.tn,
        "pt_mg_l": salida.tp,
        "ph": salida.ph,
        "coliformes_ufc_100ml": salida.coliforms,
    }
    resultados = {}
    for clave, limite in limites.items():
        if clave == "ph_min":
            cumple = salida.ph >= limite
            resultados["ph"] = {
                "valor": round(salida.ph, 2),
                "limite": f"≥ {limite:g}",
                "cumple": bool(cumple and resultados.get("ph", {}).get("cumple", True)),
            }
            continue
        if clave == "ph_max":
            previo = resultados.get("ph", {"valor": round(salida.ph, 2), "cumple": True})
            previo["limite"] = f"{previo.get('limite', '')} y ≤ {limite:g}".strip()
            previo["cumple"] = bool(previo["cumple"] and salida.ph <= limite)
            resultados["ph"] = previo
            continue
        if clave not in valores:
            continue
        valor = valores[clave]
        resultados[clave] = {
            "valor": round(valor, 2),
            "limite": f"≤ {limite:g}",
            "cumple": bool(valor <= limite),
        }
    resultados["cumple_global"] = all(
        v["cumple"] for k, v in resultados.items() if isinstance(v, dict)
    )
    return resultados


def indice_calidad_agua(s: Stream) -> dict:
    """Índice simplificado 0-100 (mayor = mejor) para el efluente.

    Combina materia orgánica, sólidos, nutrientes y patógenos con pesos
    Inspirados en el ICA de la NSF, adaptado a efluentes tratados.
    """
    def score(valor: float, bueno: float, malo: float) -> float:
        if valor <= bueno:
            return 100.0
        if valor >= malo:
            return 0.0
        return 100.0 * (malo - valor) / (malo - bueno)

    componentes = {
        "dbo5": score(s.bod5, 10.0, 100.0),
        "dqo": score(s.cod, 40.0, 300.0),
        "sst": score(s.tss, 10.0, 100.0),
        "nutrientes": score(s.tn, 5.0, 40.0),
        "patogenos": score(math.log10(max(s.coliforms, 1.0)), 2.0, 6.0),
    }
    pesos = {"dbo5": 0.30, "dqo": 0.20, "sst": 0.20, "nutrientes": 0.20, "patogenos": 0.10}
    total = sum(componentes[k] * pesos[k] for k in pesos)
    return {
        "valor": round(total, 1),
        "clasificacion": (
            "Excelente" if total >= 85 else
            "Buena" if total >= 70 else
            "Aceptable" if total >= 55 else
            "Deficiente"
        ),
        "componentes": {k: round(v, 1) for k, v in componentes.items()},
    }
