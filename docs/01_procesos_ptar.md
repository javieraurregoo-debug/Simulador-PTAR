# Fase 1 · Procesos de una PTAR

> Investigación aplicada al diseño del gemelo digital. El documento resume el
> tren de tratamiento, los parámetros de diseño y las variables de operación
> que luego se implementan en el modelo matemático y en la visualización 3D.

## 1. Alcance y normativa de referencia

Una planta de tratamiento de aguas residuales (PTAR) combina operaciones
físicas, químicas y biológicas para retirar sólidos, materia orgánica,
nutrientes y patógenos antes de la descarga o el reúso. En Colombia, la
Resolución 0631 de 2015 fija límites máximos permisibles según la actividad y
el cuerpo receptor; para agua residual doméstica los valores guía más usados
en diseño son:

| Parámetro | Límite típico de referencia | Unidad |
|---|---:|---|
| DBO5 | 50 | mg/L |
| DQO | 150 | mg/L |
| SST | 50 | mg/L |
| N total | 15 | mg/L |
| P total | 2 | mg/L |
| pH | 6,0 – 9,0 | – |
| Coliformes fecales | 1 000 | UFC/100 mL |

Los límites son configurables en la aplicación; el motor de simulación no
impone una norma específica.

## 2. Tren de tratamiento implementado

```
Afluente
   │
   ├─► Rejillas de desbaste ──► Desarenador        (pretratamiento)
   │
   ├─► Sedimentador primario                        (primario)
   │
   ├─► Reactor A2O
   │     ├─ Zona anaerobia      (liberación / selección)
   │     ├─ Zona anóxica        (desnitrificación)
   │     └─ Zona aerobia        (oxidación + nitrificación)
   │
   ├─► Sedimentador secundario ──► Desinfección ──► Efluente
   │            │
   │            └─ RAS + purga
   │
   └─► Tren de lodos
         Lodo primario + purga
              │
              ├─► Espesador por gravedad
              ├─► Digestor anaerobio ──► Biogás ──► Cogeneración
              └─► Deshidratación ──► Torta ──► Disposición
```

### 2.1 Pretratamiento

**Rejillas de desbaste.** Retienen sólidos gruesos (plásticos, textiles,
ramas) que dañarían bombas y equipos. Se diseñan con una abertura de 6–40 mm,
velocidad de aproximación de 0,6–1,0 m/s y un ángulo de inclinación de 45–75°.
La pérdida de carga se estima con la ecuación de Kirschmer:

$$
h = \beta \left(\frac{w}{b}\right)^{4/3}\frac{v^2}{2g}\sin\theta
$$

con $\beta \approx 2{,}42$ para barras rectangulares.

**Desarenador.** Separa arenas y material inorgánico denso por sedimentación
con velocidad horizontal controlada (0,25–0,35 m/s) y tiempo de retención de
45–90 s. No debe confundirse con un sedimentador primario: retira únicamente
la fracción de arena, del orden del 10–20 % de los SST.

### 2.2 Tratamiento primario

**Sedimentador primario.** Remueve sólidos suspendidos sedimentables y parte
de la materia orgánica particulada. Los rangos de diseño son:

| Variable | Rango típico |
|---|---|
| Carga superficial (SOR) | 24 – 48 m³/(m²·d) |
| Tiempo de retención | 1,5 – 2,5 h |
| Profundidad | 3,0 – 4,0 m |
| Remoción de SST | 50 – 70 % |
| Remoción de DBO5 | 25 – 40 % |

El modelo implementado integra una distribución lognormal de velocidades de
sedimentación (mediana 45 m/d, $\sigma_{\ln}=0{,}9$) sobre la eficiencia de
Hazen corregida por dispersión hidráulica.

### 2.3 Tratamiento secundario: lodos activados A2O

El tren **A2O** (anaerobio–anóxico–aerobio) elimina simultáneamente materia
orgánica, nitrógeno y fósforo:

| Zona | Condición | Proceso dominante | TRH típico |
|---|---|---|---|
| Anaerobia | Sin O₂ ni NO₃ | Selección de PAO, liberación de P | 1 – 2 h |
| Anóxica | Sin O₂, con NO₃ | Desnitrificación | 2 – 4 h |
| Aerobia | O₂ 1,5 – 2,5 mg/L | Oxidación de COD y nitrificación | 6 – 12 h |

Variables de control:

- **SRT (edad del lodo):** 10–25 d para nitrificación estable en clima cálido.
- **F/M:** 0,05–0,25 kg DQO/(kg SSV·d) para aireación extendida.
- **MLSS:** 2 500–4 500 mg/L.
- **RAS:** 0,5–1,5 × Q.
- **Recirculación interna:** 2–4 × Q para desnitrificación.
- **OD en zona aerobia:** 1,5–2,5 mg/L; por debajo de 1,5 mg/L se inhibe la
  nitrificación.
- **SVI:** 80–150 mL/g. Por encima de 180 mL/g se sospecha bulking.

**Nitrificación.** Las bacterias autótrofas (*Nitrosomonas* y *Nitrobacter*)
oxidan el amonio a nitrato. Consumen 4,57 g O₂ por g N y 7,14 g de alcalinidad
como CaCO₃ por g N, por lo que el pH puede descender.

**Desnitrificación.** En la zona anóxica los heterótrofos usan nitrato como
aceptor de electrones y recuperan 3,57 g de alcalinidad por g N. Requiere
recirculación interna del licor mixto desde la zona aerobia.

**Eliminación biológica de fósforo.** Los organismos acumuladores de
polifosfato (PAO) liberan fósforo en condiciones anaerobias y lo captan en
exceso en condiciones aerobias. En este proyecto el módulo de fósforo se
simplifica a asimilación en la biomasa; la remoción intensiva requeriría
dosificación de coagulante (por ejemplo, sulfato de aluminio o cloruro férrico).

### 2.4 Sedimentador secundario

Separa el licor mixto en efluente clarificado y lodo de retorno. El diseño se
verifica con el **análisis de punto de estado** y la curva de flujo de sólidos
de Vesilind:

$$
v_s(X) = V_0 e^{-KX}, \qquad G(X) = X\,(v_s(X) + u)
$$

donde $u = Q_{sub}/A$ es la velocidad de arrastre. Si la carga aplicada supera
el flujo límite, el manto de lodos asciende y los sólidos escapan por el
rebose. Valores de diseño: SOR 12–24 m³/(m²·d), carga de sólidos 4–6 kg/(m²·h),
profundidad 3,5–4,5 m.

### 2.5 Desinfección

| Método | Mecanismo | Dosis típica | Nota |
|---|---|---|---|
| Cloro | Oxidación de pared celular | 3–8 mg/L, CT 60–120 mg·min/L | Genera subproductos |
| UV | Daño al ADN | 20–40 mJ/cm² | Sensible a turbidez |
| Ozono | Oxidación fuerte | 2–8 mg/L | Mayor costo energético |

La inactivación se modela con Chick-Watson:

$$
\log_{10}\frac{N}{N_0} = -k\,C^n\,t\,f_T\,f_{pH}
$$

### 2.6 Tratamiento de lodos

- **Espesamiento:** 2–3 % → 4–6 % de sólidos.
- **Digestión anaerobia:** 20–30 d de TRH, destrucción de 40–50 % de SSV,
  producción de 0,8–1,1 m³ de biogás por kg de SSV destruido (60–65 % CH₄).
- **Deshidratación:** torta de 20–30 % de sólidos; captura de 90–95 %.
- **Rechazos:** el sobrenadante y el filtrado se recirculan a cabecera; pueden
  incrementar la carga de DQO y SST entre 2 % y 10 %.

## 3. Problemas operativos frecuentes

| Síntoma | Causa probable | Acción |
|---|---|---|
| Sólidos en el efluente | Punto de estado superado, SVI alto | Reducir carga, ajustar RAS, revisar purga |
| Nitrificación incompleta | OD bajo, SRT corto, temperatura baja | Aumentar aireación o SRT |
| Espuma biológica | *Nocardia*, *Microthrix* | Reducir SRT, eliminar grasas, selector anóxico |
| Bulking filamentoso | Baja relación F/M, déficit de nutrientes | Ajustar F/M, dosificar nutrientes |
| pH bajo | Nitrificación sin alcalinidad suficiente | Dosificar alcalinidad |
| Olor en digestor | Sobrecarga o cortocircuito | Estabilizar alimentación y temperatura |

## 4. Datos de diseño del caso base

| Parámetro | Valor |
|---|---:|
| Caudal | 9 000 m³/d |
| DBO5 | 240 mg/L |
| DQO | 455 mg/L |
| SST | 230 mg/L |
| NTK | 42 mg/L |
| P total | 7 mg/L |
| Volumen anaerobio / anóxico / aerobio | 900 / 1 800 / 5 400 m³ |
| RAS | 0,8 |
| Recirculación interna | 3,0 |
| Purga | 180 m³/d |
| SVI | 140 mL/g |

## 5. Referencias

1. Metcalf & Eddy, AECOM (2014). *Wastewater Engineering: Treatment and
   Resource Recovery*, 5th ed. McGraw-Hill.
2. Henze, M., Grady, C.P.L., Gujer, W., Marais, G.v.R., Matsuo, T. (1987).
   *Activated Sludge Model No. 1*. IAWPRC Scientific and Technical Report No. 1.
3. von Sperling, M. (2007). *Activated Sludge and Aerobic Biofilm Reactors*.
   IWA Publishing.
4. Tchobanoglous, G., Burton, F.L., Stensel, H.D. (2003). *Wastewater
   Engineering: Treatment and Reuse*, 4th ed.
5. Ministerio de Ambiente y Desarrollo Sostenible de Colombia (2015).
   Resolución 0631 de 2015.
