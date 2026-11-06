"""
Parámetros cinéticos y estequiométricos del modelo biológico.

Los valores corresponden a un modelo reducido derivado de ASM1
(Activated Sludge Model No. 1, Henze et al., 1987) y de los rangos
recomendados en Metcalf & Eddy (2014) y von Sperling (2007).

Todos los coeficientes están referidos a 20 °C y se corrigen por
temperatura con factores de Arrhenius theta**(T-20) en biological.py.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Heterótrofos (crecimiento sobre sustrato fácilmente biodegradable)
# ---------------------------------------------------------------------------
MU_H = 4.0          # 1/d    tasa máxima de crecimiento heterótrofo
K_S = 10.0          # gCOD/m3 constante de semisaturación para S_S
K_OH = 0.20         # gO2/m3 constante de semisaturación para O2 (heterótrofos)
K_NO = 0.50         # gN/m3  constante de semisaturación para NO3 (desnitrificación)
ETA_G = 0.80        # -      factor de corrección del crecimiento anóxico
B_H = 0.40          # 1/d    tasa de decaimiento heterótrofo
Y_H = 0.65          # gCOD/gCOD rendimiento de biomasa heterótrofa

# ---------------------------------------------------------------------------
# Hidrólisis del sustrato lentamente biodegradable
# ---------------------------------------------------------------------------
K_H = 3.0           # 1/d    tasa máxima de hidrólisis
K_X = 0.10          # gCOD/gCOD semisaturación (X_S/X_BH)
ETA_H = 0.70        # -      factor de corrección de la hidrólisis anóxica

# ---------------------------------------------------------------------------
# Autótrofos (nitrificantes)
# ---------------------------------------------------------------------------
MU_A = 0.80         # 1/d    tasa máxima de crecimiento autótrofo
K_NH = 1.0          # gN/m3  semisaturación para amonio
K_OA = 0.40         # gO2/m3 semisaturación de O2 para nitrificantes
B_A = 0.08          # 1/d    tasa de decaimiento autótrofo
Y_A = 0.20          # gCOD/gN rendimiento de biomasa autótrofa

# ---------------------------------------------------------------------------
# Estequiometría
# ---------------------------------------------------------------------------
F_I = 0.08          # -      fracción inerte de la biomasa en decaimiento
I_NXB = 0.086       # gN/gCOD nitrógeno en la biomasa
I_NXS = 0.05        # gN/gCOD nitrógeno en el sustrato particulado
I_XI = 0.06         # gN/gCOD nitrógeno en inertes particulados

O2_POR_NH4 = 4.57   # gO2/gN   demanda de oxígeno de la nitrificación completa
ALK_POR_NH4 = 7.14  # g CaCO3/gN alcalinidad consumida al nitrificar
ALK_POR_NO3 = 3.57  # g CaCO3/gN alcalinidad recuperada al desnitrificar

# ---------------------------------------------------------------------------
# Fósforo (módulo simplificado de eliminación biológica, bio-P)
# ---------------------------------------------------------------------------
K_REL = 4.0         # 1/d     tasa de liberación anaerobia de polifosfato
K_BH_P = 500.0      # gCOD/m3 semisaturación de biomasa para la liberación
K_UPT = 0.20        # gP/(gCOD·d) tasa de captación aerobia de fósforo
K_P = 0.50          # gP/m3  semisaturación para la captación de PO4
Y_PP = 0.10         # gP/gCOD contenido máximo de polifosfato por biomasa

# ---------------------------------------------------------------------------
# Coeficientes de corrección por temperatura (theta)
# ---------------------------------------------------------------------------
THETA_MU_H = 1.10
THETA_B_H = 1.04
THETA_MU_A = 1.07
THETA_B_A = 1.03
THETA_K_H = 1.04
THETA_K_REL = 1.04

# ---------------------------------------------------------------------------
# Sedimentación secundaria (Vesilind / análisis de punto de estado)
# ---------------------------------------------------------------------------
# v_s = V0 * exp(-K * X)   con X en g/L y v_s en m/h
V0_BASE = 9.0       # m/h   velocidad de sedimentación de referencia (SVI = 100)
K_BASE = 0.45       # L/g   coeficiente de compresibilidad (SVI = 100)
V0_SVI = 0.005      # 1/(mL/g) sensibilidad de V0 al SVI
K_SVI = 0.0035      # L/(g·mL/g) sensibilidad de K al SVI

# ---------------------------------------------------------------------------
# Transferencia de oxígeno
# ---------------------------------------------------------------------------
ALPHA = 0.60        # -     factor alpha (agua residual vs agua limpia)
BETA = 0.95         # -     factor beta (salinidad / tensoactivos)
CS_20 = 9.09        # g/m3  solubilidad de O2 a 20 °C y 1 atm
F_OX_SUP = 0.25     # -     fracción de oxígeno en peso en el aire
RHO_AIRE = 1.205    # kg/m3 densidad del aire a 20 °C
O2_DENS = 1.429     # kg/m3 densidad del oxígeno
EFICIENCIA_SOPLADOR = 0.65
ALTITUD_PRESION = 101.325  # kPa

# ---------------------------------------------------------------------------
# Lodos
# ---------------------------------------------------------------------------
SOLIDOS_PRIMARIO = 0.025   # fracción de sólidos en lodo primario
SOLIDOS_ESPESADO = 0.045   # fracción de sólidos tras espesamiento
SOLIDOS_ESPESADOR_RECHAZO = 0.0008
SOLIDOS_TORTA = 0.22       # fracción de sólidos en torta deshidratada
VS_DESTRUIDO = 0.45        # fracción de sólidos volátiles destruidos en digestión
BIOGAS_POR_VS = 1.0        # m3 biogas / kg VS destruido
CH4_FRACCION = 0.63        # fracción de metano en el biogas
PODER_CAL_CH4 = 35.8       # MJ/m3 CH4
EFICIENCIA_ELECTRICA_CHP = 0.35   # cogeneración: electricidad / energía del CH4
EFICIENCIA_TERMICA_CHP = 0.50     # cogeneración: calor útil / energía del CH4
