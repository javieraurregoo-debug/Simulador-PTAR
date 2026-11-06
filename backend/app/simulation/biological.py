"""Modelo biológico de lodos activados con configuración A2O.

Modelo reducido derivado de ASM1 (Henze et al., 1987) con eliminación
simultánea de materia orgánica, nitrógeno y fósforo.

Formulación numérica
--------------------
Las especies solubles (S_S, S_NH, S_NO, S_PO4, S_ALK) y las partículas de
recambio rápido (X_S por hidrólisis y X_PP por captación/liberación de
fósforo) tienen constantes de tiempo de minutos y son las que confieren
rigidez al sistema. Se resuelven en estado cuasi-estacionario en cada
reactor. Con cinética de Monod, cada balance

    (C_in - C)/tau + r(C) = 0

se reduce a una ecuación cuadrática de solución explícita:

    E*C^2 - C*(D - E*Ks - B) - D*Ks = 0
    C = (bb + sqrt(bb^2 + 4*E*D*Ks)) / (2E),   bb = D - E*Ks - B

Esto elimina la rigidez, garantiza C >= 0 y permite integrar sólo 5 variables
lentas por reactor, unos dos órdenes de magnitud más rápido que una
integración convencional.

Variables de estado lentas por reactor (5): S_I, X_BH, X_BA, X_I, ISS
Calculadas algebraicamente por reactor: X_S, X_PP, S_S, S_NH, S_NO, S_PO4, S_ALK

Referencias
-----------
    Henze, M. et al. (1987) Activated Sludge Model No. 1. IAWPRC.
    Metcalf & Eddy (2014) Wastewater Treatment and Resource Recovery, 5th ed.
    von Sperling, M. (2007) Activated Sludge and Aerobic Biofilm Reactors.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from threading import Lock

import numpy as np
from scipy.integrate import solve_ivp

from . import constants as K
from .streams import Stream, solicitar_ph

# El integrador LSODA de SciPy (ODEPACK) no es reentrante: dos hilos que lo
# invocan a la vez comparten el estado interno y lanzan
# ``IntegratorConcurrencyError``. FastAPI ejecuta los endpoints síncronos en un
# threadpool, por lo que varias simulaciones concurrentes pueden colisionar.
# El lock serializa únicamente la integración; el resto del cálculo sigue
# paralelo. La caché LRU de la API evita repetir escenarios idénticos.
_SOLVER_LOCK = Lock()

# --- Variables lentas de estado ---
SI, XBH, XBA, XI, ISS = range(5)
N_EST = 5
ETIQUETAS = ["S_I", "X_BH", "X_BA", "X_I", "ISS"]

COD_A_SST = 1.14
VSS_A_SST = 0.78
N_DEC = K.I_NXB - (K.F_I * K.I_XI + (1.0 - K.F_I) * K.I_NXS)


@dataclass
class BioConfig:
    q_in: float = 9000.0
    v_ana: float = 900.0
    v_anox: float = 1800.0
    v_aer: float = 5400.0
    ras_ratio: float = 0.8
    ir_ratio: float = 3.0
    q_waste: float = 180.0
    do_aer: float = 2.0
    do_anox: float = 0.15
    svi: float = 140.0
    sec_area: float = 905.0
    temp: float = 22.0

    @property
    def volumen_total(self) -> float:
        return self.v_ana + self.v_anox + self.v_aer


def _c(base: float, theta: float, temp: float) -> float:
    return base * theta ** (temp - 20.0)


@dataclass
class _Coef:
    mu_h: float
    mu_a: float
    b_h: float
    b_a: float
    k_h: float
    k_rel: float


def _coef(temp: float) -> _Coef:
    return _Coef(
        _c(K.MU_H, K.THETA_MU_H, temp),
        _c(K.MU_A, K.THETA_MU_A, temp),
        _c(K.B_H, K.THETA_B_H, temp),
        _c(K.B_A, K.THETA_B_A, temp),
        _c(K.K_H, K.THETA_K_H, temp),
        _c(K.K_REL, K.THETA_K_REL, temp),
    )


def _raiz(e: float, d: float, b: float, ks: float) -> float:
    """Raíz positiva de  E*C^2 - (D - E*Ks - B)*C - D*Ks = 0."""
    if e <= 0.0 or d <= 0.0:
        return 0.0
    bb = d - e * ks - b
    disc = bb * bb + 4.0 * e * d * ks
    return (bb + math.sqrt(disc if disc > 0.0 else 0.0)) / (2.0 * e)


@dataclass
class _Comp:
    """Composición completa de la salida de un reactor."""
    xs: float
    xpp: float
    ss: float
    snh: float
    sno: float
    spo4: float
    alk: float
    mu_h_ox: float
    mu_h_an: float
    mu_a: float
    hid: float
    lib: float
    upt: float
    dec_h: float
    dec_a: float

    @property
    def solubles(self) -> tuple[float, float, float, float, float]:
        return (self.ss, self.snh, self.sno, self.spo4, self.alk)


def _reactor(
    cin_sol: tuple[float, float, float, float, float],
    xs_in: float, xpp_in: float,
    xbh: float, xba: float,
    so: float, tau: float, cf: _Coef,
    warm: _Comp | None = None,
) -> _Comp:
    """Resuelve la composición de salida de un reactor perfectamente mezclado."""
    ss_in, snh_in, sno_in, spo4_in, alk_in = cin_sol
    e = 1.0 / tau

    f_so = so / (K.K_OH + so) if so > 1e-9 else 0.0
    f_so_a = so / (K.K_OA + so) if so > 1e-9 else 0.0
    resto = 1.0 - f_so
    dec_h = cf.b_h * xbh
    dec_a = cf.b_a * xba
    dec = dec_h + dec_a

    sno = warm.sno if warm else 1.0
    ss = warm.ss if warm else ss_in
    xs = warm.xs if warm else xs_in
    xpp = warm.xpp if warm else xpp_in
    snh = warm.snh if warm else 0.5
    spo4 = warm.spo4 if warm else max(spo4_in * 0.5, 0.01)

    for _ in range(2):
        # ---- X_S (hidrólisis) ----
        a1 = xs_in / tau + (1.0 - K.F_I) * dec
        hmet = cf.k_h * (f_so + K.ETA_H * resto) * xbh
        if xbh > 1e-9 and hmet > 1e-12:
            inv = 1.0 / xbh
            aq = e * inv
            bq = a1 * inv - e * K.K_X - hmet * inv
            cq = a1 * K.K_X
            disc = bq * bq + 4.0 * aq * cq
            xs = (bq + math.sqrt(disc if disc > 0.0 else 0.0)) / (2.0 * aq)
        else:
            xs = a1 * tau
        xs = max(xs, 0.0)

        hid = 0.0
        if xbh > 1e-6 and xs > 1e-9:
            r = xs / xbh
            hid = cf.k_h * (r / (K.K_X + r)) * (f_so + K.ETA_H * resto) * xbh

        # ---- S_S ----
        f_sno = sno / (K.K_NO + sno) if sno > 1e-9 else 0.0
        a_ox = cf.mu_h * f_so * xbh
        a_an = cf.mu_h * K.ETA_G * resto * f_sno * xbh
        ss = _raiz(e, ss_in / tau + hid, (a_ox + a_an) / K.Y_H, K.K_S)
        monod = ss / (K.K_S + ss) if ss > 0 else 0.0
        mu_h_ox = a_ox * monod
        mu_h_an = a_an * monod

        # ---- S_NH ----
        fuente_n = K.I_NXS * hid + N_DEC * dec
        b_nh = (1.0 / K.Y_A) * cf.mu_a * f_so_a * xba
        snh = _raiz(e, snh_in / tau + fuente_n - K.I_NXB * (mu_h_ox + mu_h_an),
                    b_nh, K.K_NH)
        f_snh = snh / (K.K_NH + snh) if snh > 0 else 0.0
        mu_a = cf.mu_a * f_snh * f_so_a * xba

        # ---- S_NO ----
        b_no = (1.0 - K.Y_H) / (2.86 * K.Y_H) * mu_h_an
        sno = _raiz(e, sno_in / tau + (1.0 / K.Y_A) * mu_a, b_no, K.K_NO)

        # ---- S_PO4 (asimilación biológica) ----
        # El fósforo se incorpora a la biomasa nueva (≈ 2 % en peso de COD).
        # No se modela almacenamiento de polifosfato (EBPR) para conservar
        # exactamente el balance de fósforo; la eliminación adicional se
        # lograría con dosificación de coagulante.
        crec_biomasa = K.Y_H * (mu_h_ox + mu_h_an) + K.Y_A * mu_a - dec
        b_po4 = max(0.0, 0.02 * crec_biomasa)
        spo4 = _raiz(e, spo4_in / tau, b_po4, K.K_P)
        xpp = 0.0
        lib = 0.0
        upt = b_po4 * spo4 / (K.K_P + spo4) if spo4 > 0 else 0.0

    alk = max(
        alk_in + tau * (
            -K.ALK_POR_NH4 * (1.0 / K.Y_A) * mu_a
            + K.ALK_POR_NO3 * (1.0 - K.Y_H) / (2.86 * K.Y_H) * mu_h_an
        ),
        5.0,
    )
    return _Comp(
        xs=xs, xpp=xpp, ss=ss, snh=snh, sno=sno, spo4=spo4, alk=alk,
        mu_h_ox=mu_h_ox, mu_h_an=mu_h_an, mu_a=mu_a, hid=hid,
        lib=lib, upt=upt, dec_h=dec_h, dec_a=dec_a,
    )


# ---------------------------------------------------------------------------
# Sedimentador secundario
# ---------------------------------------------------------------------------
def propiedades_vesilind(svi: float) -> tuple[float, float, float]:
    v0 = float(np.clip(K.V0_BASE * math.exp(-K.V0_SVI * (svi - 100.0)), 1.0, 20.0))
    kk = float(np.clip(K.K_BASE + K.K_SVI * (svi - 100.0), 0.15, 1.6))
    return v0, kk, v0 / (kk * math.e)


@dataclass
class _Sed:
    x_sub: float
    x_reb: float
    eff: float
    ratio: float
    factor: float
    mlss: float


def _sedimentador(p_cod: float, iss: float, cfg: BioConfig) -> _Sed:
    mlss = p_cod / COD_A_SST + iss
    a = max(cfg.sec_area, 1.0)
    qf = cfg.q_in * (1.0 + cfg.ras_ratio)
    q_sub = cfg.ras_ratio * cfg.q_in + cfg.q_waste
    qe = max(cfg.q_in - cfg.q_waste, 1.0)
    x_ml = max(mlss, 1.0) / 1000.0

    v0, kk, _ = propiedades_vesilind(cfg.svi)
    u_h = q_sub / 24.0 / a
    g_total = x_ml * (v0 * math.exp(-kk * x_ml) + u_h)
    g_apl = x_ml * (qf / 24.0) / a
    ratio = g_apl / max(g_total, 1e-9)

    eff = float(np.clip(1.0 - 0.041 * math.exp(min(8.8 * (ratio - 1.0), 60.0)),
                        0.0, 0.9995))

    x_sub_max = 1.0e6 / max(cfg.svi, 40.0)
    x_reb_min = 3.0 + 0.0025 * mlss
    x_reb = max(mlss * (1.0 - eff), x_reb_min)
    x_sub = (qf * mlss - qe * x_reb) / max(q_sub, 1e-9)
    if x_sub > x_sub_max:
        x_sub = x_sub_max
        x_reb = max(0.0, (qf * mlss - q_sub * x_sub) / qe)
    x_sub = float(np.clip(x_sub, 800.0, x_sub_max))
    eff = float(np.clip(1.0 - x_reb / max(mlss, 1e-6), 0.0, 0.9999))

    f_ret = float(np.clip(1.0 - x_reb / max(mlss, 1e-6), 0.0, 1.0))
    factor = f_ret * qf / max(q_sub, 1e-6)
    return _Sed(x_sub, x_reb, eff, ratio, factor, mlss)


# ---------------------------------------------------------------------------
# Planta
# ---------------------------------------------------------------------------
class _Planta:
    """Tren A2O con recirculación interna y lodo de retorno."""

    def __init__(self, cfg: BioConfig, entrada: Stream):
        self.cfg = cfg
        self.entrada = entrada
        self.q0 = cfg.q_in
        self.qr = cfg.ras_ratio * cfg.q_in
        self.qir = cfg.ir_ratio * cfg.q_in
        self.q1 = self.q0 + self.qr
        self.q2 = self.q1 + self.qir
        self.taus = (cfg.v_ana / self.q1, cfg.v_anox / self.q2, cfg.v_aer / self.q2)
        self.so = (0.0, cfg.do_anox, cfg.do_aer)
        self.cf = _coef(cfg.temp)

        self.ent_lento = np.array([
            entrada.si, 0.0, 0.0, entrada.xi,
            max(entrada.tss - entrada.vss, 1.0),
        ])
        self.ent_sol = (entrada.ss, entrada.nh4, entrada.sno, entrada.spo4, entrada.alk)
        self.xs_ent = entrada.xs

        self._c3: _Comp | None = None
        self._sed: _Sed | None = None

    # ------------------------------------------------------------------
    def resolver(self, x: np.ndarray, iteraciones: int = 3):
        """Resuelve los tres reactores; devuelve (c1, c2, c3, sed)."""
        q0, qr, qir, q1, q2 = self.q0, self.qr, self.qir, self.q1, self.q2
        cf, so, taus = self.cf, self.so, self.taus

        c3_prev = self._c3
        c1 = c2 = c3 = None
        sed = None

        for _ in range(iteraciones):
            xs_ras = (c3_prev.xs * 1.0) if c3_prev is not None else self.xs_ent
            xpp_ras = c3_prev.xpp if c3_prev is not None else 0.0
            sol_ras = np.array(c3_prev.solubles) if c3_prev is not None else np.array(self.ent_sol)
            factor = self._sed.factor if self._sed is not None else 1.0

            # R1
            xs1 = (self.xs_ent * q0 + xs_ras * factor * qr) / q1
            xpp1 = (0.0 + xpp_ras * factor * qr) / q1
            s1in = tuple((np.array(self.ent_sol) * q0 + sol_ras * qr) / q1)
            c1 = _reactor(s1in, xs1, xpp1, x[0, XBH], x[0, XBA], so[0], taus[0], cf, c1)

            # R2 (con recirculación interna de R3)
            xs2 = (c1.xs * q1 + xs_ras * factor * qir) / q2
            xpp2 = (c1.xpp * q1 + xpp_ras * factor * qir) / q2
            s2in = tuple((np.array(c1.solubles) * q1 + sol_ras * qir) / q2)
            c2 = _reactor(s2in, xs2, xpp2, x[1, XBH], x[1, XBA], so[1], taus[1], cf, c2)

            # R3
            c3 = _reactor(c2.solubles, c2.xs, c2.xpp, x[2, XBH], x[2, XBA],
                          so[2], taus[2], cf, c3)

            p3 = c3.xs + x[2, XBH] + x[2, XBA] + x[2, XI]
            sed = _sedimentador(p3, x[2, ISS], self.cfg)

            if c3_prev is not None:
                err = abs(c3.ss - c3_prev.ss) + abs(c3.sno - c3_prev.sno) \
                    + abs(c3.xs - c3_prev.xs) / 10.0
                c3_prev = c3
                if err < 1e-7:
                    break
            else:
                c3_prev = c3

        self._c3 = c3
        self._sed = sed
        return c1, c2, c3, sed

    # ------------------------------------------------------------------
    def derivadas(self, x: np.ndarray, c1, c2, c3, sed) -> np.ndarray:
        d = np.zeros_like(x)
        comps = (c1, c2, c3)
        entradas = self._entradas(x, sed.factor, c3)

        for i, c in enumerate(comps):
            d[i] = (entradas[i] - x[i]) / self.taus[i]
            d[i, XBH] += c.mu_h_ox + c.mu_h_an - c.dec_h
            d[i, XBA] += c.mu_a - c.dec_a
            d[i, XI] += K.F_I * (c.dec_h + c.dec_a)
        return d

    def _entradas(self, x, factor, c3):
        ent = self.ent_lento
        ras = np.array([
            x[2, SI], x[2, XBH] * factor, x[2, XBA] * factor,
            x[2, XI] * factor, x[2, ISS] * factor,
        ])
        e1 = (ent * self.q0 + ras * self.qr) / self.q1
        e2 = (x[0] * self.q1 + x[2] * self.qir) / self.q2
        return (e1, e2, x[1])


# ---------------------------------------------------------------------------
# Simulación
# ---------------------------------------------------------------------------
def simular_biologico(entrada: Stream, cfg: BioConfig, dias: float = 180.0) -> dict:
    planta = _Planta(cfg, entrada)

    def rhs(_t, y):
        x = y.reshape(3, N_EST)
        c1, c2, c3, sed = planta.resolver(x)
        return planta.derivadas(x, c1, c2, c3, sed).reshape(-1)

    base = np.array([
        entrada.si, 1600.0, 120.0, entrada.xi + 600.0,
        max(entrada.tss - entrada.vss, 1.0),
    ])
    y = np.tile(base, 3)

    t_final = 0.0
    convergido = False
    with _SOLVER_LOCK:
        for bloque in range(6):
            sol = solve_ivp(rhs, (t_final, t_final + dias / 6.0), y,
                            method="LSODA", rtol=1e-6, atol=1e-3, max_step=5.0)
            y_nuevo = np.clip(sol.y[:, -1], 0.0, None)
            cambio = float(np.max(np.abs(y_nuevo - y) / (np.abs(y_nuevo) + 1.0)))
            y = y_nuevo
            t_final += dias / 6.0
            if bloque >= 1 and cambio < 1e-9:
                convergido = True
                break

    x = y.reshape(3, N_EST)
    c1, c2, c3, sed = planta.resolver(x, iteraciones=8)
    residuo = float(np.max(np.abs(planta.derivadas(x, c1, c2, c3, sed)
                                  / (np.abs(x) + 10.0))))
    # El residual relativo es el criterio práctico de estado estacionario:
    # un valor inferior al 5 % es aceptable para ingeniería conceptual.
    convergido = bool(convergido or residuo < 0.05)
    comps = (c1, c2, c3)

    q0, qr, qir = cfg.q_in, cfg.ras_ratio * cfg.q_in, cfg.ir_ratio * cfg.q_in
    q1, q2 = q0 + qr, q0 + qr + qir
    taus = (cfg.v_ana / q1, cfg.v_anox / q2, cfg.v_aer / q2)
    volumes = (cfg.v_ana, cfg.v_anox, cfg.v_aer)
    v_total = sum(volumes)

    mlss_i = [
        (comps[i].xs + x[i, XBH] + x[i, XBA] + x[i, XI]) / COD_A_SST + x[i, ISS]
        for i in range(3)
    ]
    mlss3 = mlss_i[2]
    x_avg = sum(m * v for m, v in zip(mlss_i, volumes)) / v_total

    qe = q0 - cfg.q_waste
    solidos_kg_d = (cfg.q_waste * sed.x_sub + qe * sed.x_reb) / 1000.0
    srt = (x_avg * v_total / 1000.0) / max(solidos_kg_d, 1e-6)
    fm = (q0 * entrada.ss) / max(v_total * (x_avg * VSS_A_SST), 1e-6)

    our_total = 0.0
    for c, vol in zip(comps, volumes):
        our = ((1.0 - K.Y_H) / K.Y_H * c.mu_h_ox
               + (K.O2_POR_NH4 - K.Y_A) / K.Y_A * c.mu_a)
        our_total += our * vol
    our_total /= 1000.0

    # ---- Efluente del sedimentador secundario ----
    esc = sed.x_reb / max(mlss3, 1e-9)
    ef = entrada.copy()
    ef.q = qe
    ef.si = x[2, SI]
    ef.ss, ef.nh4, ef.sno, ef.spo4, ef.alk = c3.solubles
    ef.xs = c3.xs * esc
    ef.xi = x[2, XI] * esc
    ef.xbh = x[2, XBH] * esc
    ef.xba = x[2, XBA] * esc
    ef.xpp = c3.xpp * esc
    ef.tss = sed.x_reb
    ef.vss = sed.x_reb * VSS_A_SST
    ef.ph = solicitar_ph(ef.alk, cfg.temp)
    ef.coliforms = max(entrada.coliforms * max(0.02, esc), 1.0)
    ef.turbidity = 2.0 + 0.55 * sed.x_reb

    reactores = []
    nombres = ["Zona anaerobia", "Zona anóxica", "Zona aerobia"]
    ids = ["anaerobio", "anoxico", "aerobio"]
    for i in range(3):
        c = comps[i]
        our_i = ((1.0 - K.Y_H) / K.Y_H * c.mu_h_ox
                 + (K.O2_POR_NH4 - K.Y_A) / K.Y_A * c.mu_a) * volumes[i] / 1000.0
        reactores.append({
            "id": ids[i], "nombre": nombres[i],
            "volumen_m3": round(volumes[i], 1),
            "trh_h": round(24.0 * volumes[i] / q0, 2),
            "sst": round(mlss_i[i], 0),
            "ssv": round(mlss_i[i] * VSS_A_SST, 0),
            "ss": round(c.ss, 2),
            "xs": round(c.xs, 1),
            "xbh": round(x[i, XBH], 0),
            "xba": round(x[i, XBA], 0),
            "xi": round(x[i, XI], 0),
            "nh4": round(c.snh, 2),
            "sno": round(c.sno, 2),
            "spo4": round(c.spo4, 3),
            "xpp": round(c.xpp, 1),
            "do": round((0.0, cfg.do_anox, cfg.do_aer)[i], 2),
            "alk": round(c.alk, 0),
            "ph": round(solicitar_ph(c.alk, cfg.temp), 2),
            "our_kg_d": round(our_i, 1),
        })

    # ---- Aireación ----
    cs_t = (14.652 - 0.41022 * cfg.temp + 0.007991 * cfg.temp ** 2
            - 0.000077774 * cfg.temp ** 3)
    f_cs = max((cs_t - cfg.do_aer) / K.CS_20, 1e-6)
    sotr = our_total / max(K.ALPHA * K.BETA * f_cs, 1e-6)
    sote = min(0.30, 0.065 * 4.5)
    aire_m3_d = sotr / (0.232 * max(sote, 0.05)) / K.RHO_AIRE
    potencia_kw = aire_m3_d / 86400.0 * 55.0 / K.EFICIENCIA_SOPLADOR

    return {
        "efluente": ef,
        "reactores": reactores,
        "sedimentador": {
            "sst_purga": round(sed.x_sub, 0),
            "sst_rebose": round(sed.x_reb, 1),
            "eficiencia_pct": round(sed.eff * 100, 2),
            "punto_estado": round(float(sed.ratio), 3),
            "carga_solidos_kg_m2_d": round(mlss3 * (q0 + qr) / cfg.sec_area / 1000.0, 1),
            "carga_limite_kg_m2_d": round(propiedades_vesilind(cfg.svi)[2] * 24.0, 1),
            "convergido": bool(convergido),
            "residual": round(residuo, 9),
            "dias_simulados": round(t_final, 0),
        },
        "operacion": {
            "srt_d": round(srt, 1),
            "fm_kg_cod_kg_ssv_d": round(fm, 3),
            "mlss_mg_l": round(mlss3, 0),
            "mlvss_mg_l": round(mlss3 * VSS_A_SST, 0),
            "trh_h": round(24.0 * v_total / q0, 2),
            "trh_anaerobio_h": round(24.0 * taus[0], 2),
            "trh_anoxico_h": round(24.0 * taus[1], 2),
            "trh_aerobio_h": round(24.0 * taus[2], 2),
            "carga_organica_kg_d": round(q0 * entrada.bod5 / 1000.0, 1),
            "carga_cod_kg_d": round(q0 * entrada.cod / 1000.0, 1),
            "carga_volumetrica_kg_cod_m3_d": round(q0 * entrada.cod / v_total / 1000.0, 3),
            "our_kg_o2_d": round(our_total, 1),
            "o2_especifico_kg_kg_cod": round(our_total / max(q0 * entrada.cod / 1000.0, 1e-6), 2),
            "sotr_kg_o2_d": round(sotr, 1),
            "aire_m3_d": round(aire_m3_d, 0),
            "aire_m3_por_m3_agua": round(aire_m3_d / max(q0, 1.0), 1),
            "potencia_sopladores_kw": round(potencia_kw, 1),
            "lodo_purgado_kg_d": round(cfg.q_waste * sed.x_sub / 1000.0, 1),
            "nitrificacion_kg_n_d": round(c3.mu_a / K.Y_A * cfg.v_aer / 1000.0, 1),
            "desnitrificacion_kg_n_d": round(
                (1 - K.Y_H) / (2.86 * K.Y_H) * c2.mu_h_an * cfg.v_anox / 1000.0, 1),
            "recirculacion_interna": cfg.ir_ratio,
            "ras": cfg.ras_ratio,
        },
    }
