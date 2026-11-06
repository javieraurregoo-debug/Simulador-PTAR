"""Operaciones unitarias físicas: pretratamiento, sedimentación y desinfección.

Cada función recibe una corriente de entrada y devuelve la corriente de salida
más un diccionario con los indicadores de diseño de la unidad.
"""

from __future__ import annotations

import math

import numpy as np

from . import constants as K
from .streams import Stream, normalizar_concentraciones, solicitar_ph


# ---------------------------------------------------------------------------
# Utilidades geométricas
# ---------------------------------------------------------------------------
def area_circular(n: int, diametro_m: float) -> float:
    return max(n, 1) * math.pi * diametro_m ** 2 / 4.0


# ---------------------------------------------------------------------------
# 1. Rejillas de desbaste
# ---------------------------------------------------------------------------
def rejillas(
    entrada: Stream,
    espaciamiento_mm: float = 20.0,
    velocidad_m_s: float = 0.75,
    angulo_grados: float = 60.0,
) -> tuple[Stream, dict]:
    """Cribado por rejillas.

    La eficiencia de retención de sólidos gruesos se relaciona con la
    abertura libre mediante una ley de potencia calibrada con los valores
    habituales de operación (2-12 % de SST para aberturas de 6-40 mm).

    La pérdida de carga se estima con la ecuación de Kirschmer:

        h = beta * (w / b)^(4/3) * (v^2 / 2g) * sin(theta)

    con beta = 2,42 para barras rectangulares de sección circular.
    """
    b = max(espaciamiento_mm, 3.0) / 1000.0            # m, abertura
    w = 0.008                                            # m, espesor de barra
    beta = 2.42
    g = 9.81
    v = max(velocidad_m_s, 0.2)
    h = beta * (w / b) ** (4.0 / 3.0) * (v ** 2 / (2 * g)) * math.sin(math.radians(angulo_grados))

    # Retención de sólidos gruesos
    frac_solidos = float(np.clip(0.02 + 2.5 * math.log10(b / 0.006) * 0.01, 0.02, 0.12))
    frac_solidos = float(np.clip(frac_solidos, 0.015, 0.12))
    frac_cod = 0.35 * frac_solidos
    frac_coli = 0.10 * frac_solidos

    salida = entrada.copy()
    for f in ("xs", "xi", "xbh", "xba"):
        setattr(salida, f, getattr(salida, f) * (1 - frac_cod))
    salida.tss *= 1 - frac_solidos
    salida.vss *= 1 - frac_solidos * 0.9
    salida.coliforms *= 1 - frac_coli
    salida.turbidity *= 1 - 0.6 * frac_solidos

    info = {
        "id": "rejillas",
        "nombre": "Rejillas de desbaste",
        "detalle": f"Abertura {espaciamiento_mm:.0f} mm, v = {velocidad_m_s:.2f} m/s",
        "perdida_carga_m": round(h, 4),
        "remocion_sst_pct": round(frac_solidos * 100, 1),
        "remocion_cod_pct": round(frac_cod * 100, 1),
    }
    return normalizar_concentraciones(salida), info


# ---------------------------------------------------------------------------
# 2. Desarenador
# ---------------------------------------------------------------------------
def desarenador(
    entrada: Stream,
    t_h_s: float = 60.0,
    velocidad_m_s: float = 0.30,
) -> tuple[Stream, dict]:
    """Desarenado por flujo horizontal.

    El desarenador no es un sedimentador primario: sólo retira la fracción
    de arena y material inorgánico denso, que representa del orden del 10-20 %
    de los SST de un agua municipal. La captura de arenas sigue una cinética
    de primer orden con el tiempo de retención:

        eta_arena = 0,90 * (1 - exp(-t / 30))
        eta_SST   = f_arena * eta_arena          f_arena ≈ 0,15

    La velocidad horizontal se limita a 0,30 m/s para evitar resuspensión.
    """
    t = max(t_h_s, 5.0)
    eta_arena = 0.90 * (1.0 - math.exp(-t / 30.0))
    f_arena = 0.15
    eta = f_arena * eta_arena
    if velocidad_m_s > 0.35:
        eta *= 1 - min(0.6, (velocidad_m_s - 0.35) / 0.4)

    # La arena es inorgánica: se retira SST y SSV en la misma proporción
    salida = entrada.copy()
    salida.tss *= 1 - eta
    salida.vss *= 1 - eta
    for f in ("xs", "xi", "xbh", "xba"):
        setattr(salida, f, getattr(salida, f) * (1 - eta * 0.30))
    salida.coliforms *= 1 - eta * 0.05
    salida.turbidity *= 1 - eta * 0.15

    info = {
        "id": "desarenador",
        "nombre": "Desarenador",
        "detalle": f"TRH {t:.0f} s, v = {velocidad_m_s:.2f} m/s",
        "remocion_arena_pct": round(eta_arena * 100, 1),
        "remocion_sst_pct": round(eta * 100, 1),
        "remocion_cod_pct": round(eta * 30, 1),
        "volumen_m3": round(entrada.q * t / 86400.0, 1),
        "arena_kg_d": round(entrada.q * entrada.tss * eta / 1000.0, 1),
    }
    return normalizar_concentraciones(salida), info


# ---------------------------------------------------------------------------
# 3. Sedimentador primario (modelo de Hazen + tanques en serie)
# ---------------------------------------------------------------------------
def _eta_particula(v_s_m_d: float, v_c_m_d: float, n_serie: float) -> float:
    """Eficiencia para partículas de velocidad v_s en un tanque tipo CSTR en serie.

    Modelo de dispersión de Weber: un sedimentador real se aproxima a N
    reactores perfectamente mezclados en serie. Para N -> infinito el
    comportamiento tiende al flujo pistón (eficiencia ideal de Hazen).
    """
    ratio = v_s_m_d / max(v_c_m_d, 1e-6)
    return 1.0 - (1.0 + ratio / n_serie) ** (-n_serie)


def sedimentador_primario(
    entrada: Stream,
    n_unidades: int = 2,
    diametro_m: float = 14.0,
    profundidad_m: float = 3.5,
    v50_m_d: float = 45.0,
    sigma_ln: float = 0.9,
) -> tuple[Stream, dict]:
    """Sedimentación primaria de partículas discretas/floculentas.

    Se discretiza la distribución lognormal de velocidades de sedimentación
    del agua residual municipal (mediana 45 m/d, sigma 0,9) y se integra la
    eficiencia de Hazen corregida por dispersión hidráulica.

    Valores típicos de diseño: SOR 24-48 m3/(m2·d), TRH 1,5-2,5 h.
    """
    a = area_circular(n_unidades, diametro_m)
    v = a * profundidad_m
    sor = entrada.q / max(a, 1e-6)             # m3/(m2·d) = m/d
    hrt_h = 24.0 * v / max(entrada.q, 1e-6)

    # Número de tanques en serie equivalente (dispersión hidráulica)
    n_serie = float(np.clip(1.0 + 2.0 * hrt_h, 1.0, 6.0))

    # Distribución lognormal de velocidades de sedimentación
    u = np.linspace(0.001, 0.999, 257)
    from scipy.special import ndtri

    z = ndtri(u)
    vs = v50_m_d * np.exp(sigma_ln * z)
    pesos = np.diff(u, prepend=0.0)

    eta_tss = float(np.sum(pesos * np.array([_eta_particula(x, sor, n_serie) for x in vs])))
    eta_tss = float(np.clip(eta_tss, 0.05, 0.92))

    # Resuspensión: si la velocidad horizontal es alta se pierde eficiencia
    v_h = entrada.q / 86400.0 / (n_unidades * max(diametro_m, 1.0) * profundidad_m)
    if v_h > 0.012:
        eta_tss *= 1 - min(0.25, (v_h - 0.012) / 0.05)

    salida = entrada.with_removal(frac_particulate=eta_tss, frac_soluble=0.0)
    salida.coliforms *= 1 - 0.35 * eta_tss
    salida.turbidity = entrada.turbidity * (1 - 0.88 * eta_tss)

    # Lodo primario
    solidos_kg_d = entrada.q * entrada.tss * eta_tss / 1000.0
    lodo_m3_d = solidos_kg_d / (K.SOLIDOS_PRIMARIO * 1000.0)

    # DBO5 removida (solo la asociada al material particulado)
    bod_rem = entrada.bod5 * eta_tss * 0.85

    info = {
        "id": "primario",
        "nombre": "Sedimentador primario",
        "detalle": f"{n_unidades} × Ø{diametro_m:.1f} m, prof. {profundidad_m:.1f} m",
        "area_m2": round(a, 1),
        "volumen_m3": round(v, 1),
        "sor_m3_m2_d": round(sor, 1),
        "trh_h": round(hrt_h, 2),
        "carga_superficial": round(sor, 1),
        "remocion_sst_pct": round(eta_tss * 100, 1),
        "remocion_dbo_pct": round(bod_rem / max(entrada.bod5, 1e-6) * 100, 1),
        "remocion_cod_pct": round(eta_tss * 85, 1),
        "lodo_m3_d": round(lodo_m3_d, 1),
        "solidos_kg_d": round(solidos_kg_d, 1),
    }
    return normalizar_concentraciones(salida), info


# ---------------------------------------------------------------------------
# 4. Sedimentador secundario (análisis de punto de estado)
# ---------------------------------------------------------------------------
def propiedades_vesilind(svi: float) -> tuple[float, float, float]:
    """Coeficientes de Vesilind en función del SVI.

    Devuelve (V0 [m/h], K [L/g], flujo límite [kg/(m2·h)]).
    """
    v0 = K.V0_BASE * math.exp(-K.V0_SVI * (svi - 100.0) * 1000.0 / 1000.0)
    kk = K.K_BASE + K.K_SVI * (svi - 100.0) * 1000.0 / 1000.0
    v0 = float(np.clip(v0, 1.0, 20.0))
    kk = float(np.clip(kk, 0.15, 1.6))
    flujo_limite = v0 / (kk * math.e)     # kg/(m2·h)
    return v0, kk, flujo_limite


def sedimentador_secundario(
    entrada: Stream,
    q_alimentacion: float,
    q_ras: float,
    q_purga: float,
    n_unidades: int = 2,
    diametro_m: float = 24.0,
    profundidad_m: float = 4.0,
    svi: float = 140.0,
) -> tuple[Stream, Stream, dict]:
    """Sedimentador secundario con separación de sólidos por punto de estado.

    A partir del SVI se obtiene la curva de flujo de sólidos de Vesilind:

        v_s(X) = V0 * exp(-K * X)
        G_t(X) = X * (v_s(X) + u)          u = Q_sub/A  (velocidad de arrastre)

    El "punto de estado" se ubica en (X_ML, G_aplicado). Si el punto cae por
    encima de la curva, el manto de lodos asciende y los sólidos escapan por
    el rebose. La eficiencia de captura se modela con una función logística
    calibrada para reproducir el fallo progresivo observado en planta.
    """
    a = area_circular(n_unidades, diametro_m)
    qf = entrada.q
    x_ml = max(entrada.tss, 1.0) / 1000.0             # kg/m3
    q_sub = q_ras + q_purga
    u = q_sub / 86400.0 / max(a, 1e-6)                # m/h (velocidad de arrastre)
    u = u * 24.0                                       # m/d -> convertir abajo

    # velocidades en m/h
    u_h = q_sub / 24.0 / max(a, 1e-6)                  # m/h
    v0, kk, g_lim = propiedades_vesilind(svi)
    v_s = v0 * math.exp(-kk * x_ml)
    g_total = x_ml * (v_s + u_h)                       # kg/(m2·h)
    g_aplicado = x_ml * (qf / 24.0) / max(a, 1e-6)     # kg/(m2·h)
    ratio = g_aplicado / max(g_total, 1e-6)

    # Eficiencia de captura: 1 - 0.041*exp(8.8*(ratio-1))
    eff = 1.0 - 0.041 * math.exp(8.8 * (ratio - 1.0))
    eff = float(np.clip(eff, 0.0, 0.9995))

    qe = max(qf - q_purga, 1.0)

    # Los sólidos no sedimentables escapan siempre del clarificador.
    # Se impone un rebose mínimo de 3-10 mg/L según el manto de lodos.
    x_reb_min = 3.0 + 0.0025 * entrada.tss
    x_rebose = max(entrada.tss * (1.0 - eff), x_reb_min)

    # Concentración máxima de la purga (limitada por el SVI)
    x_sub_max = 1.0e6 / max(svi, 40.0)                 # mg/L
    x_sub = (qf * entrada.tss - qe * x_rebose) / max(q_sub, 1e-6)
    if x_sub > x_sub_max:
        x_sub = x_sub_max
        x_rebose = max(0.0, (qf * entrada.tss - q_sub * x_sub) / qe)
    x_sub = max(x_sub, 800.0)
    eff = float(np.clip(1.0 - x_rebose / max(entrada.tss, 1e-6), 0.0, 0.9999))

    # ------- Corriente de rebose (efluente del secundario) -------
    efluente = entrada.copy()
    efluente.q = qe
    # Los solubles pasan sin cambio; el particulado se retiene
    frac_ret = 1.0 - x_rebose / max(entrada.tss, 1e-6)
    frac_ret = float(np.clip(frac_ret, 0.0, 1.0))
    for f in ("xs", "xi", "xbh", "xba"):
        setattr(efluente, f, getattr(efluente, f) * frac_ret)
    efluente.tss = x_rebose
    efluente.vss = entrada.vss * frac_ret
    efluente.turbidity = 2.0 + 0.55 * x_rebose
    efluente.coliforms = entrada.coliforms * max(0.02, frac_ret)

    # ------- Corriente de fondo (RAS + purga) -------
    ras = entrada.copy()
    ras.q = q_sub
    for f in ("xs", "xi", "xbh", "xba"):
        setattr(ras, f, getattr(ras, f) * (qf / max(q_sub, 1e-6)) * frac_ret)
    ras.tss = x_sub
    ras.vss = min(x_sub * 0.80, x_sub)
    ras.coliforms = entrada.coliforms * 20

    info = {
        "id": "secundario",
        "nombre": "Sedimentador secundario",
        "detalle": f"{n_unidades} × Ø{diametro_m:.1f} m, SVI {svi:.0f} mL/g",
        "area_m2": round(a, 1),
        "sor_m3_m2_d": round(qf / max(a, 1e-6), 1),
        "carga_solidos_kg_m2_d": round(g_aplicado * 24.0, 1),
        "flujo_limite_kg_m2_d": round(g_total * 24.0, 1),
        "punto_estado": round(ratio, 3),
        "eficiencia_captura_pct": round(eff * 100, 2),
        "sst_rebose_mg_l": round(x_rebose, 1),
        "sst_purga_mg_l": round(x_sub, 0),
    }
    return normalizar_concentraciones(efluente), normalizar_concentraciones(ras), info


# ---------------------------------------------------------------------------
# 5. Desinfección
# ---------------------------------------------------------------------------
def desinfeccion(
    entrada: Stream,
    metodo: str = "cloro",
    dosis_mg_l: float = 4.0,
    tiempo_contacto_min: float = 30.0,
    dosis_uv_mj_cm2: float = 30.0,
    ozono_mg_l: float = 0.0,
) -> tuple[Stream, dict]:
    """Desinfección por cloro (Chick-Watson), UV o ozono.

    Cloro:  log10(N/N0) = -k * C^n * t * f_T * f_pH
            k = 0,60 L/(mg·min) para coliformes fecales a 20 °C, n = 1
            f_T = 1,05^(T-20), f_pH corrige la especiación HOCl/OCl-
    UV:     log10(N/N0) = -D / D90, con D90 ≈ 6 mJ/cm2 para coliformes
            (dosis de referencia; se aplica un factor de calidad del agua
            por turbidez porque las partículas protegen a los microorganismos)
    Ozono:  CT con k = 2,5 L/(mg·min)
    """
    salida = entrada.copy()
    n0 = max(entrada.coliforms, 1.0)
    t = max(tiempo_contacto_min, 0.0)

    if metodo == "cloro":
        # Fracción de HOCl (más eficaz) según pH
        ph = entrada.ph
        f_ph = 1.0 / (1.0 + 10 ** (ph - 7.5))
        f_ph = 0.35 + 0.65 * f_ph
        f_t = 1.05 ** (entrada.temp - 20.0)
        # Demanda de cloro ejercida por el efluente (materia orgánica residual)
        demanda = 0.55 + 0.0045 * entrada.cod
        c_libre = max(dosis_mg_l - demanda, 0.0)
        k = 0.60
        log_rem = k * c_libre * t * f_ph * f_t
        ct = c_libre * t
        metodo_detalle = f"Cloro {dosis_mg_l:.1f} mg/L, CT = {ct:.0f} mg·min/L"
        cloro_residual = c_libre
    elif metodo == "uv":
        d90 = 6.0
        # La turbidez y los sólidos atenúan la transmitancia
        f_calidad = math.exp(-0.012 * entrada.turbidity) * math.exp(-0.02 * entrada.tss)
        dosis_efectiva = dosis_uv_mj_cm2 * max(f_calidad, 0.05)
        log_rem = dosis_efectiva / d90
        ct = dosis_uv_mj_cm2
        metodo_detalle = f"UV {dosis_uv_mj_cm2:.0f} mJ/cm² (útil {dosis_efectiva:.1f})"
        cloro_residual = 0.0
    elif metodo == "ozono":
        demanda = 0.8 + 0.006 * entrada.cod
        c_res = max(ozono_mg_l - demanda, 0.0)
        log_rem = 2.5 * c_res * t
        ct = c_res * t
        metodo_detalle = f"Ozono {ozono_mg_l:.1f} mg/L, CT = {ct:.0f} mg·min/L"
        cloro_residual = 0.0
    else:
        log_rem = 0.0
        ct = 0.0
        metodo_detalle = "Sin desinfección"
        cloro_residual = 0.0

    log_rem = float(np.clip(log_rem, 0.0, 8.0))
    salida.coliforms = max(n0 / 10 ** log_rem, 1.0)
    salida.turbidity = entrada.turbidity * 0.97

    info = {
        "id": "desinfeccion",
        "nombre": "Desinfección",
        "detalle": metodo_detalle,
        "metodo": metodo,
        "inactivacion_log": round(log_rem, 2),
        "ct": round(ct, 1),
        "cloro_residual_mg_l": round(cloro_residual, 2),
        "coliformes_salida": round(salida.coliforms, 0),
    }
    return normalizar_concentraciones(salida), info
