# Fase 4 · Visualización 3D con Three.js

> La escena 3D es un **gemelo digital dirigido por datos**: la geometría, las
> etiquetas y los colores se construyen a partir del catálogo del backend y del
> resultado de la simulación. React monta la escena una sola vez; los cambios
> de escenario actualizan materiales y textos sin recrear la planta.

## 1. Objetivos

1. Representar las 13 unidades del tren de agua y del tren de lodos con una
   lectura visual inmediata.
2. Traducir la simulación en señales visuales: calidad del agua, intensidad de
   aireación, producción de biogás y flujos de recirculación.
3. Mantener 60 fps en un portátil con gráficos integrados, sin librerías de
   gráficas ni React Three Fiber.
4. Permitir inspeccionar cada unidad con clic y enfocarla con doble clic.
5. Ser accesible y responsive: etiquetas HTML nítidas, botones con `aria` y
   una vista alternativa en tablas para todos los datos.

## 2. Stack y archivos

| Elemento | Tecnología | Archivo |
|---|---|---|
| Render | Three.js 0.169 | `frontend/src/three/PlantScene.js` |
| Controles | `OrbitControls` | addons de Three.js |
| Etiquetas | `CSS2DRenderer` | addons de Three.js |
| Montaje React | `useEffect` + refs | `frontend/src/components/SceneView.jsx` |
| Controles de vista | React | `frontend/src/components/SceneToolbar.jsx` |
| Ficha de unidad | React | `frontend/src/components/UnitInspector.jsx` |
| Perfil 2D | SVG puro | `frontend/src/components/ProfileChart.jsx` |
| Estilos | CSS | `frontend/src/styles.css` |

La escena se implementa como una **clase imperativa** (`PlantScene`) y no como
componentes declarativos. Esto evita que cada render de React reconstruya
geometrías, texturas y materiales, y deja explícito el ciclo de vida:

```js
const escena = new PlantScene(container, { onSelect });
escena.setCatalog(catalogo.unidades);
escena.update(resultado);
// ...
escena.dispose();
```

## 3. Grafo de escena

```
PlantScene
├── Scene
│   ├── Sky sphere (shader de degradado)
│   ├── Ground plane + GridHelper
│   ├── HemisphereLight + DirectionalLight (sombras) + fill + ambient
│   ├── Patio del tren de lodos
│   ├── Letrero de la planta
│   ├── Unidades (Map id → Group)
│   │   ├── Losa de concreto
│   │   ├── Geometría según `forma`
│   │   ├── Superficie de agua (material físico animado)
│   │   ├── Burbujas (solo zona aerobia)
│   │   ├── Llama y luz (solo digestor)
│   │   └── CSS2DObject (etiqueta HTML)
│   ├── Tuberías (TubeGeometry sobre CatmullRomCurve3)
│   ├── Partículas de flujo (esferas que recorren las curvas)
│   └── Anillo de selección (TorusGeometry)
├── PerspectiveCamera (44°)
├── WebGLRenderer (ACESFilmic, sombras PCF suaves)
├── CSS2DRenderer (capa HTML superpuesta)
└── OrbitControls (damping, zoom y paneo limitados)
```

La cámara parte de una vista alta de tres cuartos:

```js
camera.position.set(-4, 62, 60);
controls.target.set(4, 0, 6);
```

Esta posición reduce el solapamiento entre el tren de agua (eje X) y el tren de
lodos (Z ≈ 18), que en una vista isométrica baja quedaba oculto por el
sedimentador secundario.

## 4. Catálogo de unidades

`GET /api/catalogo` devuelve `unidades[]`; cada entrada contiene:

| Campo | Uso |
|---|---|
| `id` | Clave estable para datos, selección y tuberías |
| `nombre`, `descripcion`, `tipo` | Etiqueta y ficha del inspector |
| `forma` | `canal`, `tanque`, `cilindro`, `digestor` o `edificio` |
| `posicion` | Coordenadas `[x, y, z]` del grupo |
| `dimensiones` | `[ancho, alto, profundidad]` en unidades de escena |
| `color` | Color base del agua y de las paredes |
| `parametros_clave` | Variables que resalta el inspector |

### 4.1 Unidades y geometría

| Unidad | Forma | Posición (x, z) | Rasgo visual |
|---|---|---|---|
| Afluente | Canal | −42, 0 | Entrada del agua cruda |
| Rejillas | Canal | −35, 0 | Siete barras metálicas |
| Desarenador | Canal | −27.5, 0 | Canal alargado |
| Primario | Cilindro | −16, 0 | Tanque circular con puente |
| Anaerobio | Tanque | −4, 0 | Agitador y agua violeta |
| Anóxico | Tanque | 4.5, 0 | Agitador y agua índigo |
| Aerobio | Tanque | 17, 0 | Difusores y 160 burbujas |
| Secundario | Cilindro | 31, 0 | Tanque circular de 24 m |
| Desinfección | Canal | 43, 0 | Techo verde translúcido |
| Efluente | Canal | 51, 0 | Salida del agua tratada |
| Espesador | Cilindro | 6, 18 | Lodo marrón |
| Digestor | Digestor | −8, 18 | Domo, llama y luz de biogás |
| Deshidratación | Edificio | −23, 18 | Nave con ventanas y chimenea |

Las dimensiones son **simbólicas**, no están a escala métrica: se eligieron para
que el conjunto quepa en cámara y para que cada equipo sea reconocible. El
catálogo es la única fuente de verdad; cambiar una posición en el backend mueve
la unidad, sus tuberías y su etiqueta sin tocar el frontend.

### 4.2 Construcción por forma

- **`canal`**: fondo, dos paredes y una lámina de agua. Rejillas añade barras;
  desinfección añade una cubierta translúcida.
- **`tanque`**: cuatro paredes, fondo y agua. La zona aerobia añade difusores y
  un sistema de partículas; las demás añaden motor y eje de agitación.
- **`cilindro`**: pared cilíndrica abierta, fondo, borde metálico, puente,
  barandas y columna central. Se usa en primario, secundario y espesador.
- **`digestor`**: cuerpo cilíndrico, domo semiesférico, cono inferior, escalera,
  tubo de gas, llama animada y `PointLight` cálida.
- **`edificio`**: volumen principal, losa de cubierta, ventanas emisivas, puerta
  y chimenea.

Cada unidad recibe una losa de concreto y proyecta sombras. El agua usa
`MeshPhysicalMaterial` con una textura de cáusticas generada en canvas; su
`offset` se anima en el bucle para dar sensación de movimiento.

## 5. Tuberías y flujos

Las conexiones viven en `CONEXIONES` dentro de `PlantScene.js`:

```js
{ from: "aerobio", to: "anoxico", kind: "recirculacion", via: [[11, 1.8, 6.5]] }
```

| Tipo | Color | Uso |
|---|---|---|
| `agua` | Azul petróleo | Tren principal |
| `lodo` | Marrón | Primario/secundario → espesador → digestor |
| `recirculacion` | Ámbar | RAS y recirculación interna |
| `rechazo` | Gris azulado | Sobrenadante y filtrado a cabecera |

Para cada conexión se calculan los puntos de entrada y salida a partir de las
dimensiones de las unidades, se añaden los vértices `via` y se construye una
`CatmullRomCurve3`. Sobre la curva se genera un `TubeGeometry` y varias esferas
emisivas; en cada frame las esferas avanzan con `getPointAt(u)` y reinician su
recorrido. La velocidad global se escala con el caudal tratado:

```js
flowSpeed = clamp(caudal / 9000, 0.5, 2.4);
```

## 6. Etiquetas HTML y colisiones

Se usa `CSS2DRenderer`: cada etiqueta es un `div.unit-label` anclado a un
`CSS2DObject`. Ventajas frente a `Sprite`/texto 3D: tipografía nítida a
cualquier distancia, selección de texto y estilos CSS.

Cada etiqueta muestra el nombre y un resumen dinámico:

- Afluente: `DQO 455 mg/L`.
- Pretratamiento y primario: `DQO … · SST …`.
- Reactores: `SST … · N-NH₄ …`.
- Secundario: `SST … · η … %`.
- Digestor: `Biogás … m³/d`.
- Deshidratación: `Torta … kg SST/d`.

Las etiquetas se apilan en el espacio 3D con alturas distintas por unidad
(`alturaEtiqueta`) para reducir el solapamiento inicial. Aun así, en vistas
alejadas pueden chocar; por eso cada 12 frames se ejecuta un pase de colisión:

1. Se ordenan por prioridad (seleccionada primero; luego afluente, secundario,
   aerobio, digestor, efluente…).
2. Se comparan los rectángulos en pantalla con margen de 3 px.
3. Si hay choque y la etiqueta no está seleccionada, se oculta con
   `is-hidden`; la seleccionada siempre permanece visible.

El pase se ejecuta a 5 Hz, no en cada frame, para no forzar *layout* continuo.

## 7. Cámara, navegación e interacción

| Acción | Resultado |
|---|---|
| Arrastrar | Orbita alrededor del objetivo |
| Rueda | Zoom (10–145 unidades) |
| Clic en unidad | Selecciona, abre `UnitInspector` y muestra el anillo |
| Doble clic | Vuela al encuadre de la unidad |
| Botón «Enfocar en 3D» | Igual que doble clic desde la ficha |
| `⟲` | Vuelve a la vista isométrica |

Vistas predefinidas (`setView`):

| Vista | Posición | Objetivo |
|---|---|---|
| Isométrica | `[-4, 62, 60]` | `[4, 0, 6]` |
| Aérea | `[4, 88, 26]` | `[4, 0, 5]` |
| Tren de agua | `[46, 24, 50]` | `[12, 2, 0]` |
| Tren de lodos | `[2, 32, 54]` | `[-5, 2, 15]` |

Los cambios de cámara usan un *tween* con suavizado `easeInOutQuad` de 0,75–0,9 s.
El raycasting recorre los grupos de unidades y sube por los padres hasta
encontrar `userData.unitId`; así basta con marcar el grupo raíz.

## 8. Actualización con la simulación

`PlantScene.update(resultado)` no reconstruye la escena. Convierte las listas
`etapas`, `reactores` y `tren_lodos.etapas` en mapas por `id` y actualiza:

| Señal visual | Fuente |
|---|---|
| Color del agua | DQO de salida (`qualityHex`) |
| Texto de etiqueta | DQO, SST, NH₄, remoción o biogás |
| Burbujas | `operacion_biologica.aire_m3_d` |
| Llama y luz | `tren_lodos.etapas[digestor].biogas_m3_d` |
| Velocidad de partículas | `kpis.caudal_tratado_m3_d` |
| Anillo de selección | Unidad seleccionada |

La escala de color va de cian limpio a ámbar sucio según la DQO:

```js
t = clamp((DQO - 20) / 430, 0, 1);
hue = 195 - 165 * t;   // 195° cian → 30° ámbar
```

El inspector consulta la misma respuesta y muestra métricas, balances y
parámetros de diseño de la unidad. No hay cálculo duplicado en el cliente.

## 9. Controles de visualización

`SceneToolbar` expone cuatro *toggles*:

- **Etiquetas**: muestra u oculta la capa CSS2D.
- **Flujos**: muestra u oculta las partículas de las tuberías.
- **Calidad**: colorea el agua por DQO; al desactivarlo vuelve al color base.
- **Rotación**: órbita automática lenta alrededor del objetivo.

La leyenda inferior explica la escala de carga orgánica y los cuatro tipos de
tubería. Los botones usan `aria-pressed` y `title` para teclado y lectores de
pantalla.

## 10. Rendimiento

| Medida | Implementación |
|---|---|
| Resolución | `setPixelRatio(min(devicePixelRatio, 2))` |
| Sombras | Un solo `DirectionalLight` con mapa de 2048² |
| Geometría | Primitivas reutilizadas; sin modelos externos |
| Actualización | `update()` solo al recibir un resultado nuevo |
| Etiquetas | Pase de colisión cada 12 frames |
| Cámara | `OrbitControls` con damping y límites de distancia/ángulo |
| Memoria | `dispose()` de geometrías, materiales, texturas, controles y renderer |
| Bundle | Three.js importado por módulos; sin R3F ni librería de gráficas |

El bucle de animación usa un `THREE.Clock` con `dt` acotado a 0,06 s para evitar
saltos tras cambiar de pestaña. Las animaciones (burbujas, flujo, llama, anillo)
son independientes de React y no provocan renders del árbol de componentes.

## 11. Responsive y accesibilidad

- La escena observa su contenedor con `ResizeObserver` y actualiza cámara y
  renderer al cambiar el layout.
- En pantallas estrechas el panel de control pasa a una columna superior y la
  escena conserva una altura mínima.
- Todas las cifras críticas están también en tablas y tarjetas HTML, por lo que
  la información no depende de percibir el 3D.
- Los botones tienen texto visible o `aria-label`; la ficha usa `aria-label`.
- El color no es el único canal: las etiquetas y los valores numéricos acompañan
  la escala de calidad.

## 12. Limitaciones y trabajo futuro

1. **Geometría simbólica.** No es un modelo BIM ni respeta distancias reales.
2. **Sin colisiones físicas.** Las tuberías pueden cruzarse visualmente con
   equipos en ciertas vistas.
3. **Un solo tren.** No se representan unidades redundantes (2 tanques
   primarios, sopladores de reserva).
4. **Sin nivel freático ni terreno.** El suelo es un plano con rejilla.
5. **Etiquetas 2D.** En vistas densas el pase de colisión oculta etiquetas
   secundarias; el usuario puede seleccionar una unidad, rotar la cámara o usar
   las vistas predefinidas para leerlas todas.
6. **Móvil.** El rendimiento depende de WebGL; en equipos antiguos conviene
   desactivar sombras o reducir el `pixelRatio`.

Posibles extensiones: *clipping planes* para cortar tanques, animación del nivel
de agua con el caudal, mapas de calor sobre el terreno, modo comparación de dos
escenarios y exportación de capturas.

## 13. Verificación

```bash
# 1. Backend y API
cd backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000

# 2. Frontend en desarrollo
cd frontend
npm install
npm run dev          # http://127.0.0.1:5173

# 3. Build de producción servido por FastAPI
npm run build
# http://127.0.0.1:8000/app/
```

Lista de comprobación manual:

- [ ] La escena carga las 13 unidades y las etiquetas.
- [ ] Los cuatro botones de vista mueven la cámara sin errores.
- [ ] Clic en una unidad abre la ficha con datos de la simulación.
- [ ] Doble clic enfoca la unidad.
- [ ] Los toggles de etiquetas, flujos, calidad y rotación funcionan.
- [ ] Cambiar el caudal en el panel y simular actualiza colores y velocidad.
- [ ] El digestor cambia la llama al variar la producción de biogás.
- [ ] Las pestañas `#operacion`, `#efluente`, `#lodos` y `#modelo` son
      enlazables y muestran datos.
- [ ] Redimensionar la ventana no deforma la escena.

## 14. Referencias

1. Three.js Documentation. <https://threejs.org/docs/>
2. Three.js Examples: `OrbitControls`, `CSS2DRenderer`, `TubeGeometry`.
3. React Documentation. <https://react.dev/>
4. Vite Documentation. <https://vitejs.dev/>
5. Metcalf & Eddy (2014). *Wastewater Engineering*, 5th ed. — criterios de
   representación y nomenclatura de unidades.
