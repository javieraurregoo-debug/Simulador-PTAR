"""Representación de una corriente de agua residual."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace


@dataclass
class Stream:
    """Corriente de agua residual.

    Las concentraciones están en g/m3 (= mg/L), los caudales en m3/d.
    La DBO5 y el nitrógeno total se derivan de la especiación de la materia
    orgánica y no se almacenan por separado, de modo que el balance de masa
    se mantiene siempre cerrado.
    """

    q: float = 0.0          # m3/d
    si: float = 0.0         # COD soluble inerte
    ss: float = 0.0         # COD soluble fácilmente biodegradable
    xs: float = 0.0         # COD particulado lentamente biodegradable
    xi: float = 0.0         # COD particulado inerte
    xbh: float = 0.0        # biomasa heterótrofa (COD)
    xba: float = 0.0        # biomasa autótrofa (COD)
    tss: float = 0.0        # sólidos suspendidos totales
    vss: float = 0.0        # sólidos suspendidos volátiles
    nh4: float = 0.0        # N amoniacal
    sno: float = 0.0        # N de nitratos
    spo4: float = 0.0       # P ortofosfato
    xpp: float = 0.0        # P almacenado como polifosfato (lodo)
    alk: float = 250.0      # alcalinidad, mg/L como CaCO3
    ph: float = 7.2
    temp: float = 20.0
    coliforms: float = 0.0  # UFC/100 mL
    turbidity: float = 0.0  # NTU

    # ------------------------------------------------------------------
    # Propiedades derivadas
    # ------------------------------------------------------------------
    @property
    def cod(self) -> float:
        """Demanda química de oxígeno total (mg/L)."""
        return self.si + self.ss + self.xs + self.xi + self.xbh + self.xba

    @property
    def COD(self) -> float:  # alias en mayúsculas para tablas
        return self.cod

    @property
    def particulate_cod(self) -> float:
        return self.xs + self.xi + self.xbh + self.xba

    @property
    def soluble_cod(self) -> float:
        return self.si + self.ss

    @property
    def bcod(self) -> float:
        """COD biodegradable: sustrato soluble + particulado hidrolizable + biomasa."""
        return self.ss + self.xs + self.xbh + self.xba

    @property
    def bod5(self) -> float:
        """DBO5 estimada.

        Se aplica un factor de 0,65 g DBO5/g COD biodegradable. Para agua
        residual municipal cruda esto reproduce la relación típica
        DBO5/DBO última ~ 0,68 y DBO5/COD ~ 0,5 (Metcalf & Eddy, 2014).
        """
        return 0.65 * self.bcod

    @property
    def BOD5(self) -> float:
        return self.bod5

    @property
    def tkn(self) -> float:
        """Nitrógeno total Kjeldahl = amonio + N orgánico."""
        organico = (
            self.xs * 0.05
            + (self.xbh + self.xba) * 0.086
            + self.xi * 0.06
            + self.si * 0.02
            + self.ss * 0.02
        )
        return self.nh4 + organico

    @property
    def TKN(self) -> float:
        return self.tkn

    @property
    def tn(self) -> float:
        """Nitrógeno total."""
        return self.tkn + self.sno

    @property
    def TN(self) -> float:
        return self.tn

    @property
    def tp(self) -> float:
        """Fósforo total."""
        return self.spo4 + self.xpp

    @property
    def TP(self) -> float:
        return self.tp

    @property
    def tss_vss_ratio(self) -> float:
        return self.vss / self.tss if self.tss > 1e-9 else 0.0

    # ------------------------------------------------------------------
    # Operaciones
    # ------------------------------------------------------------------
    def copy(self) -> "Stream":
        return replace(self)

    def load(self, name: str) -> float:
        """Carga másica de un constituyente en kg/d."""
        return getattr(self, name) * self.q / 1000.0

    def mix(self, other: "Stream") -> "Stream":
        """Mezcla de dos corrientes (todo mezclado, conservación de masa)."""
        qt = self.q + other.q
        if qt <= 0:
            return Stream()
        out = self.copy()
        for f in (
            "si", "ss", "xs", "xi", "xbh", "xba", "tss", "vss",
            "nh4", "sno", "spo4", "xpp", "coliforms",
        ):
            setattr(out, f, (getattr(self, f) * self.q + getattr(other, f) * other.q) / qt)
        # Parámetros no conservativos: media ponderada por caudal
        out.alk = (self.alk * self.q + other.alk * other.q) / qt
        out.temp = (self.temp * self.q + other.temp * other.q) / qt
        out.ph = (self.ph * self.q + other.ph * other.q) / qt
        out.turbidity = (self.turbidity * self.q + other.turbidity * other.q) / qt
        out.q = qt
        return out

    def scale_flow(self, q: float) -> "Stream":
        out = self.copy()
        out.q = q
        return out

    def with_removal(self, frac_particulate: float, frac_soluble: float) -> "Stream":
        """Devuelve la corriente tras remover fracciones de sólidos y solubles."""
        out = self.copy()
        for f in ("xs", "xi", "xbh", "xba"):
            setattr(out, f, getattr(out, f) * (1 - frac_particulate))
        out.tss *= 1 - frac_particulate
        out.vss *= 1 - frac_particulate
        for f in ("si", "ss"):
            setattr(out, f, getattr(out, f) * (1 - frac_soluble))
        out.coliforms *= 1 - 0.5 * frac_particulate
        out.turbidity *= 1 - 0.85 * frac_particulate
        return out


def solicitar_ph(alk: float, temp: float = 20.0) -> float:
    """Estimación de pH a partir de la alcalinidad remanente.

    Correlación empírica de compromiso: la alcalinidad de un agua residual
    municipal tamponada se agota al nitrificar y el pH cae de forma
    aproximadamente logarítmica. Se acota a 5,5-8,5 porque el modelo no
    resuelve el equilibrio carbonato completo.
    """
    alk = max(alk, 1.0)
    ph = 6.70 + 0.35 * math.log10(alk / 100.0)
    correction = -0.008 * (temp - 20.0)
    return min(8.5, max(5.5, ph + correction))


def normalizar_concentraciones(s: Stream) -> Stream:
    """Evita valores negativos por error numérico."""
    campos = (
        "si", "ss", "xs", "xi", "xbh", "xba", "tss", "vss",
        "nh4", "sno", "spo4", "xpp", "alk", "coliforms", "turbidity",
    )
    for f in campos:
        if getattr(s, f) < 0:
            setattr(s, f, 0.0)
    return s
