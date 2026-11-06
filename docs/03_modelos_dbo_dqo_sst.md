# Fase 3 · Modelado de DBO₅, DQO y SST

> El motor implementa un modelo reducido de lodos activados derivado de ASM1,
> con resolución cuasi-estacionaria de las especies rápidas. Este documento
> presenta las ecuaciones, los supuestos y un ejemplo de verificación con el
> caso base de 9 000 m³/d.

## 1. Variables de estado

Por cada reactor se integran cinco variables lentas:

| Símbolo | Descripción | Unidad |
|---|---|---|
| $S_I$ | COD soluble inerte | mg/L |
| $X_{BH}$ | biomasa heterótrofa | mg COD/L |
| $X_{BA}$ | biomasa autótrofa | mg COD/L |
| $X_I$ | COD particulado inerte | mg COD/L |
| $ISS$ | sólidos inorgánicos | mg/L |

Las especies rápidas se resuelven algebraicamente en cada reactor:
$X_S$, $S_S$, $S_{NH}$, $S_{NO}$, $S_{PO4}$ y $S_{ALK}$.

## 2. Fraccionamiento del agua residual

El usuario caracteriza el afluente con DBO₅, DQO, SST y SSV. El modelo
necesita las fracciones de COD de ASM1. La traducción es:

$$
S_I = f_{SI}\,DQO, \qquad f_{SI}=0{,}06
$$

$$
bCOD = \frac{DBO_5}{f_{BOD}}, \qquad f_{BOD}=0{,}65\ \frac{\text{g DBO}_5}{\text{g COD}}
$$

$$
X_I = DQO - S_I - bCOD
$$

El COD particulado medido se estima con el factor estequiométrico
$1{,}42\ \text{g COD/g SSV}$:

$$
X_{p,med} = 1{,}42\,SSV - X_I
$$

$$
X_S = \operatorname{clamp}\left(X_{p,med},\ 0{,}15\,bCOD,\ 0{,}90\,bCOD\right),
\qquad S_S = bCOD - X_S
$$

Con esto se cumple exactamente:

$$
DQO = S_I + S_S + X_S + X_I
$$

### Ejemplo (caso base)

| Variable | Valor |
|---|---:|
| DQO | 455,0 mg/L |
| DBO₅ | 240,0 mg/L |
| SST | 230,0 mg/L |
| SSV | 185,0 mg/L |
| $S_I$ | 27,3 mg/L |
| $bCOD$ | 369,2 mg/L |
| $X_I$ | 58,5 mg/L |
| $X_S$ | 204,2 mg/L |
| $S_S$ | 165,0 mg/L |
| Verificación DQO | 455,0 mg/L ✔ |

## 3. DBO₅

La DBO₅ se calcula a partir del COD biodegradable, no se transporta como una
variable independiente. Así se garantiza que cualquier cambio en la
especiación se refleje en la DBO:

$$
DBO_5 = f_{BOD}\,\left(S_S + X_S + X_{BH} + X_{BA}\right)
$$

Para el afluente del caso base:

$$
DBO_5 = 0{,}65\,(165{,}0 + 204{,}2) = 240{,}0\ \text{mg/L}
$$

La relación DBO₅/DQO resultante es $240/455 = 0{,}53$, dentro del rango
típico municipal (0,4–0,6).

> **Limitación:** la DBO última se aproxima como $1{,}5\,DBO_5$. El modelo no
> resuelve la cinética de demanda de oxígeno en el tiempo; usa el factor de
> conversión calibrado.

## 4. Sólidos suspendidos totales

En el tren de agua, los SST se transportan como variable de estado y se
modifican por remoción física. En el reactor, los SST del licor mixto se
obtienen del COD particulado y de los inertes inorgánicos:

$$
SST = ISS + \frac{X_S + X_I + X_{BH} + X_{BA}}{i_{X}}
$$

con $i_X = 1{,}14\ \text{g COD/g SST}$ (relación aparente calibrada para lodos
activados). Los ISS son inertes: no reaccionan, pero se concentran por la
recirculación y la purga.

La fracción volátil se estima como:

$$
SSV = 0{,}78\,SST
$$

y la producción de lodo se cierra con el balance de sólidos del tren de lodos.

## 5. Reactores biológicos

### 5.1 Balance de mezcla completa

Para cada reactor $j$ y cada especie soluble o particulada lenta:

$$
\frac{C_{in,j} - C_j}{\tau_j} + r_j(C) = 0
$$

donde $\tau_j = V_j/Q_j$ es el tiempo de retención hidráulico real,
incluyendo recirculación. Para las especies rápidas, la acumulación se
desprecia (cuasi-estacionario), lo que elimina la rigidez del sistema.

### 5.2 Crecimiento heterótrofo

$$
\mu_H = \mu_{H,max}\,\frac{S_S}{K_S+S_S}\left(\frac{S_O}{K_{OH}+S_O} + \eta_g\,\frac{K_{OH}}{K_{OH}+S_O}\frac{S_{NO}}{K_{NO}+S_{NO}}\right)
$$

El primer término es la oxidación aerobia y el segundo la desnitrificación
anóxica. La corrección por temperatura es:

$$
k(T) = k_{20}\,\theta^{(T-20)}
$$

| Constante | Valor | Unidad |
|---|---:|---|
| $\mu_{H,max}$ | 4,0 | 1/d |
| $K_S$ | 10,0 | mg COD/L |
| $K_{OH}$ | 0,20 | mg O₂/L |
| $K_{NO}$ | 0,50 | mg N/L |
| $\eta_g$ | 0,80 | – |
| $b_H$ | 0,40 | 1/d |
| $Y_H$ | 0,65 | g COD/g COD |
| $\theta_{\mu H}$ | 1,10 | – |

### 5.3 Hidrólisis

$$
r_{hid} = k_H\,\frac{X_S/X_{BH}}{K_X + X_S/X_{BH}}\left(\frac{S_O}{K_{OH}+S_O} + \eta_h\,\frac{K_{OH}}{K_{OH}+S_O}\frac{S_{NO}}{K_{NO}+S_{NO}}\right)X_{BH}
$$

Esta reacción convierte $X_S$ en $S_S$ y libera nitrógeno orgánico.

### 5.4 Nitrificación

$$
\mu_A = \mu_{A,max}\,\frac{S_{NH}}{K_{NH}+S_{NH}}\,\frac{S_O}{K_{OA}+S_O}
$$

| Constante | Valor | Unidad |
|---|---:|---|
| $\mu_{A,max}$ | 0,80 | 1/d |
| $K_{NH}$ | 1,0 | mg N/L |
| $K_{OA}$ | 0,40 | mg O₂/L |
| $b_A$ | 0,08 | 1/d |
| $Y_A$ | 0,20 | g COD/g N |
| $\theta_{\mu A}$ | 1,07 | – |

Consumo de oxígeno y alcalinidad:

$$
r_{O_2,nit} = 4{,}57\,\frac{\mu_A}{Y_A}, \qquad
r_{ALK,nit} = -7{,}14\,\frac{\mu_A}{Y_A}
$$

### 5.5 Desnitrificación

$$
r_{NO} = \frac{1-Y_H}{2{,}86\,Y_H}\,\mu_{H,anóxica}
$$

$$
r_{ALK,desnit} = +3{,}57\,\frac{1-Y_H}{2{,}86\,Y_H}\,\mu_{H,anóxica}
$$

El factor 2,86 g COD/g N es el equivalente de oxígeno del nitrato.

### 5.6 Fósforo

El módulo implementado asimila fósforo en la biomasa nueva:

$$
r_{PO4} = -0{,}02\,\left(Y_H(\mu_{H,ox}+\mu_{H,an}) + Y_A\mu_A - b_H X_{BH} - b_A X_{BA}\right)
$$

$$
\frac{S_{PO4,in}-S_{PO4}}{\tau} + r_{PO4} = 0
$$

No se modela el almacenamiento de polifosfato (EBPR). Por eso la remoción de
P total es modesta (10–20 %) y el efluente puede no cumplir un límite de
2 mg/L; para ello se requeriría coagulación química.

### 5.7 Solución de la ecuación de Monod

Cada balance con cinética de Monod se reduce a una cuadrática. Para

$$
\frac{C_{in}-C}{\tau} + fuente - \frac{B\,C}{K_S+C} = 0
$$

se define $E = 1/\tau$, $D = C_{in}/\tau + fuente$ y se resuelve:

$$
C = \frac{bb + \sqrt{bb^2 + 4EDK_S}}{2E}, \qquad bb = D - EK_S - B
$$

Esta forma explícita garantiza $C \ge 0$ y evita iteraciones internas.

## 6. Sedimentador secundario

### 6.1 Curva de Vesilind

$$
v_s(X) = V_0\,e^{-KX}, \qquad X\ \text{en kg/m}^3
$$

$$
V_0 = 9{,}0\,e^{-0{,}005(SVI-100)}, \qquad K = 0{,}45 + 0{,}0035(SVI-100)
$$

### 6.2 Punto de estado

$$
G(X) = X\left(v_s(X) + \frac{Q_{sub}}{A}\right), \qquad
G_{aplicado} = \frac{X\,Q_f}{A}
$$

$$
\text{ratio} = \frac{G_{aplicado}}{G_{límite}}
$$

Si ratio > 1, el clarificador no puede transportar los sólidos hacia el fondo
y se produce arrastre. La eficiencia de captura se calcula con una logística
calibrada y se impone un rebose mínimo de sólidos no sedimentables:

$$
X_{reb,min} = 3 + 0{,}0025\,SST_{ML}\ \text{mg/L}
$$

$$
X_{reb} = \max\left(SST_{ML}(1-\eta),\ X_{reb,min}\right)
$$

El balance de sólidos cierra con la purga y el RAS:

$$
Q_f X_{ML} = Q_e X_{reb} + Q_{sub} X_{sub}
$$

## 7. Ecuaciones de diseño hidráulico

| Ecuación | Expresión |
|---|---|
| Área de tanque circular | $A = n\pi D^2/4$ |
| Carga superficial | $SOR = Q/A$ |
| Tiempo de retención | $TRH = V/Q$ |
| Carga orgánica volumétrica | $OLR = Q\,S_0/V$ |
| Relación alimento/microorganismo | $F/M = Q\,S_0/(V\,X_{VSS})$ |
| Edad del lodo | $SRT = X\,V/(Q_w X_r + Q_e X_e)$ |
| Pérdida de carga en rejillas | $h=\beta(w/b)^{4/3}(v^2/2g)\sin\theta$ |
| Sedimentación de Hazen | $\eta=1-(1+v_s/(v_cN))^{-N}$ |

## 8. Aireación y energía

El oxígeno requerido por el metabolismo es:

$$
OUR = \frac{1-Y_H}{Y_H}\,\mu_{H,ox}X_{BH} + \left(\frac{4{,}57-Y_A}{Y_A}\right)\mu_A X_{BA}
$$

La transferencia en agua residual se corrige con:

$$
SOTR = \frac{OUR}{\alpha\beta\left(\frac{C_s^*(T)-C_L}{C_{s,20}^*}\right)}
$$

$$
Q_{aire} = \frac{SOTR}{0{,}232\,SOTE\,\rho_{aire}}, \qquad
P_{sopladores} = \frac{Q_{aire}\,\Delta p}{\eta}
$$

El biogás se calcula con 1,0 m³/kg SSV destruido, 63 % de CH₄ y 35,8
MJ/m³ de CH₄. La cogeneración se evalúa con 35 % de eficiencia eléctrica.

## 9. Desinfección

**Cloro (Chick-Watson):**

$$
\log_{10}\frac{N}{N_0} = -k\,C_{libre}\,t\,f_{pH}\,f_T
$$

con $k=0{,}60$ L/(mg·min), $f_T=1{,}05^{T-20}$ y
$f_{pH}=0{,}35+0{,}65/(1+10^{pH-7{,}5})$.

**UV:**

$$
\log_{10}\frac{N}{N_0} = -\frac{D_{efectiva}}{D_{90}}, \qquad
D_{efectiva}=D\,e^{-0{,}012\,NTU}e^{-0{,}02\,SST}
$$

## 10. Tren de lodos

| Etapa | Ecuación |
|---|---|
| Espesador | $S_{sub}=0{,}90\,S_{in}$; $Q_{sub}=S_{sub}/(0{,}045\cdot1000)$ |
| Digestor | $S_{out}=S_{in}-0{,}45\cdot0{,}75\,S_{in}$ |
| Biogás | $V_{biogás}=1{,}0\,kg_{SSV,destruido}$; $V_{CH4}=0{,}63\,V_{biogás}$ |
| Energía | $E_{el}=V_{CH4}\cdot35{,}8\cdot0{,}35/3{,}6$ kWh/d |
| Deshidratación | $S_{torta}=0{,}95\,S_{in}$; $Q_{torta}=S_{torta}/(0{,}22\cdot1000)$ |
| Recirculación | $Q_{rec}=Q_{sobrenadante}+Q_{filtrado}$ |

## 11. Solución numérica

1. Se fracciona el afluente y se ejecutan las operaciones físicas.
2. Se integran las 15 variables lentas (5 por reactor) con `solve_ivp`
   (LSODA, `rtol=1e-6`, `atol=1e-3`, paso máximo 5 d).
3. En cada evaluación del lado derecho se resuelven los tres reactores y el
   sedimentador, iterando el RAS hasta 3 veces.
4. Se simulan 180 d en 6 bloques para alcanzar el estado estacionario.
5. Se reporta el residuo normalizado y el cierre de balances.

## 12. Verificación del caso base

| Indicador | Afluente | Efluente | Eficiencia |
|---|---:|---:|---:|
| DBO₅ (mg/L) | 240,0 | 3,1 | 98,8 % |
| DQO (mg/L) | 455,0 | 35,6 | 92,3 % |
| SST (mg/L) | 230,0 | 7,5 | 96,8 % |
| N total (mg/L) | 49,6 | 13,2 | 73,8 % |
| P total (mg/L) | 5,0 | 4,43 | 13,2 % |

| Variable de operación | Valor |
|---|---:|
| MLSS | 1 811 mg/L |
| SRT | 18,9 d |
| F/M | 0,129 kg DQO/(kg SSV·d) |
| OUR | 2 314 kg O₂/d |
| Aire | 67 707 m³/d |
| Biogás | 596 m³/d |
| Energía eléctrica | 1 308 kWh/d |
| Cierre de DQO | 109,1 % |
| Cierre de SST | 100,3 % |

El cierre de DQO incluye la materia oxidada en el reactor y la destruida en el
digestor; el de SST incluye la torta, los sólidos volatilizados y los residuos
de pretratamiento.

## 13. Supuestos y limitaciones

1. **Régimen permanente.** No se modelan picos horarios ni lluvia; el caudal es
   constante.
2. **Mezcla completa.** Cada zona se representa como un CSTR; no hay
   cortocircuitos ni gradientes espaciales.
3. **Fósforo simplificado.** No hay EBPR ni precipitación química.
4. **Sedimentador empírico.** La captura se calibra con una logística; no se
   resuelve CFD bifásico.
5. **Lodos.** No se modela el secado térmico ni el retorno de centrífuga con
   dinámica; se usan eficiencias típicas.
6. **Desinfección.** Chick-Watson supone cinética de primer orden y mezcla
   ideal; no considera resistencia ni reparación microbiana.
7. **Calibración.** Las constantes provienen de ASM1 y Metcalf & Eddy; para una
   planta real deben calibrarse con campañas de muestreo.

## 14. Referencias

1. Henze, M. et al. (1987). *Activated Sludge Model No. 1*. IAWPRC.
2. Metcalf & Eddy (2014). *Wastewater Engineering*, 5th ed.
3. von Sperling, M. (2007). *Activated Sludge and Aerobic Biofilm Reactors*.
4. Vesilind, P.A. (1968). Design of prototype thickeners from batch settling
   tests. *Water & Sewage Works*, 115.
5. Chick, H. (1908). An investigation of the laws of disinfection.
   *Journal of Hygiene*, 8(1).
