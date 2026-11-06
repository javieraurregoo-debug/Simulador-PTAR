# Frontend · PTAR Digital

Interfaz React 18 + Vite + Three.js para el gemelo digital de la PTAR. Consume
la API FastAPI, muestra la planta en 3D y presenta los resultados en tarjetas,
tablas y una gráfica SVG.

## 1. Requisitos

- Node.js 18+ (probado con 20.18.1)
- npm 9+
- Navegador con WebGL 2 (Chrome, Edge, Firefox o Safari recientes)

## 2. Instalación y ejecución

```powershell
cd frontend
npm install
npm run dev
```

Abrir <http://127.0.0.1:5173>. El servidor de Vite redirige `/api` a
`http://127.0.0.1:8000`, así que el backend debe estar corriendo.

Comandos:

| Comando | Efecto |
|---|---|
| `npm run dev` | Servidor de desarrollo con HMR |
| `npm run build` | Bundle de producción en `dist/` |
| `npm run preview` | Sirve el bundle localmente |

### 2.1 Build servido por FastAPI

```powershell
cd frontend
npm run build
cd ..\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Abrir <http://127.0.0.1:8000/app/>. Vite usa `base: "./"`, por lo que los
assets funcionan bajo el prefijo `/app/`.

### 2.2 API remota

Por defecto el cliente usa rutas relativas (`/api`). Para apuntar a otro
backend, crear `frontend/.env.local`:

```env
VITE_API_URL=http://192.168.1.50:8000
```

Vite inyecta la variable en tiempo de build. El backend debe permitir el origen
en `PTAR_CORS_ORIGINS`.

## 3. Estructura

```
frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.jsx                 # Punto de entrada React
    ├── App.jsx                  # Estado global, pestañas y layout
    ├── styles.css               # Tema oscuro, layout y responsive
    ├── api/client.js            # fetch, errores y cabeceras
    ├── hooks/useSimulation.js   # Carga, aborto y errores de simulación
    ├── lib/format.js            # Números es-CO, unidades y color por DQO
    ├── three/PlantScene.js      # Escena Three.js completa
    └── components/
        ├── Header.jsx           # Marca, preset y botón Simular
        ├── Tabs.jsx             # Navegación con badge de cumplimiento
        ├── ControlPanel.jsx     # Afluente, diseño y límites
        ├── SceneView.jsx        # Montaje/desmontaje de PlantScene
        ├── SceneToolbar.jsx     # Vistas, toggles y leyenda
        ├── UnitInspector.jsx    # Ficha de la unidad seleccionada
        ├── KpiCards.jsx         # Tarjetas de DBO/DQO/SST/N/energía/lodos
        ├── ProfileChart.jsx     # Perfil SVG en escala logarítmica
        ├── OperacionPanel.jsx   # Reactores, aireación y balances
        ├── EfluentePanel.jsx    # Calidad final y límites
        ├── LodosPanel.jsx       # Espesador, digestor y deshidratación
        └── ModeloPanel.jsx      # Ecuaciones, supuestos y verificación
```

## 4. Flujo de datos

```
App.jsx
  ├── GET /api/catalogo  ──► unidades 3D, ecuaciones, presets, límites
  ├── GET /api/presets/municipal ──► formulario inicial
  ├── POST /api/simulaciones ──► resultado
  │        │
  │        ├── SceneView → PlantScene.update(resultado)
  │        ├── KpiCards / Operacion / Efluente / Lodos / Modelo
  │        └── UnitInspector (unidad seleccionada)
  └── hashchange ──► pestaña activa (#planta, #operacion, …)
```

El estado vive en `App.jsx`. `useSimulation` cancela la petición anterior con
`AbortController`, expone `cargando`, `error` y `cache`, y devuelve el JSON.
`PlantScene` se actualiza de forma imperativa para no recrear la geometría en
cada render.

## 5. Escena 3D

`PlantScene` es una clase con ciclo de vida explícito:

```js
const escena = new PlantScene(container, { onSelect });
escena.setCatalog(catalogo.unidades);
escena.update(resultado);
escena.setSelected(id);
escena.setToggles({ etiquetas: true, flujos: true, calidad: true });
escena.setView("iso");     // iso | aerea | agua | lodos
escena.focusUnit("aerobio");
escena.dispose();
```

Características:

- 13 unidades construidas a partir de `forma`, `posicion`, `dimensiones` y
  `color` del catálogo.
- Tuberías `CatmullRomCurve3` + `TubeGeometry` con partículas animadas.
- Agua con textura de cáusticas generada en canvas.
- Burbujas en la zona aerobia cuya velocidad depende del aire de sopladores.
- Llama y luz en el digestor según el biogás producido.
- Etiquetas HTML (`CSS2DRenderer`) con ocultamiento por colisión cada 12 frames.
- Cámara con `OrbitControls`, tween de vistas y selección por raycasting.
- Colores de agua según DQO: cian (limpia) → ámbar (cargada).

Detalle técnico en [`../docs/04_visualizacion_3d.md`](../docs/04_visualizacion_3d.md).

## 6. Pestañas y enlaces profundos

| Hash | Contenido |
|---|---|
| `#planta` | Escena 3D, toolbar, inspector y KPIs |
| `#operacion` | Reactores, oxígeno, aireación y balances |
| `#efluente` | Calidad final, límites y perfil de concentraciones |
| `#lodos` | Espesamiento, digestión, biogás y torta |
| `#modelo` | Ecuaciones, supuestos y verificación del caso base |

La pestaña activa se sincroniza con `window.location.hash`; se puede compartir
un enlace directo a cualquier vista.

## 7. Diseño y accesibilidad

- Tema oscuro industrial con variables CSS.
- Layout de dos columnas: panel de control fijo y área de trabajo.
- En pantallas estrechas el panel pasa a una columna y la escena conserva una
  altura mínima.
- Botones con `title`, `aria-label` o `aria-pressed`.
- Las cifras también están en HTML, no solo en el canvas.
- La leyenda de calidad y los tipos de tubería acompañan al color.

## 8. Rendimiento

- `setPixelRatio(min(devicePixelRatio, 2))`.
- Sombras PCF suaves con un solo `DirectionalLight`.
- Sin React Three Fiber ni librerías de gráficas.
- `requestAnimationFrame` independiente de React.
- Pase de colisión de etiquetas a 5 Hz.
- `dispose()` de geometrías, materiales, texturas, controles y renderer al
  desmontar.
- Bundle de producción con advertencia de tamaño ajustada a 1 200 kB.

## 9. Verificación

No hay suite de pruebas unitarias de UI; la validación es por build y prueba
manual:

```powershell
npm run build
```

Lista de comprobación:

- [ ] `npm run dev` carga catálogo y simulación inicial.
- [ ] El build se sirve en `/app/` sin errores 404 de assets.
- [ ] Las 13 unidades y sus etiquetas aparecen.
- [ ] Las cuatro vistas de cámara funcionan.
- [ ] Clic y doble clic seleccionan y enfocan una unidad.
- [ ] Los toggles de etiquetas, flujos, calidad y rotación funcionan.
- [ ] Cambiar un parámetro marca «Cambios sin simular» y Simular lo actualiza.
- [ ] Las cinco pestañas y sus enlaces por hash funcionan.
- [ ] Redimensionar la ventana no deforma la escena.
- [ ] Un error del backend muestra el banner y permite reintentar.

## 10. Solución de problemas

| Síntoma | Causa probable | Acción |
|---|---|---|
| «No se pudo iniciar el gemelo digital» | Backend apagado o puerto distinto | Iniciar Uvicorn en 8000 |
| `404` en `/api/...` | Build servido sin backend o proxy mal configurado | Usar `npm run dev` o servir desde FastAPI |
| Escena en blanco | WebGL deshabilitado o error de contexto | Revisar la consola; probar otro navegador |
| Etiquetas superpuestas | Vista muy baja o zoom lejano | Usar vista isométrica/aérea o rotar |
| Assets 404 bajo `/app/` | `base` distinto de `./` | Mantener `base: "./"` en `vite.config.js` |
| Cambios sin efecto en producción | Bundle antiguo en `dist/` | Volver a ejecutar `npm run build` |

## 11. Referencias

1. React. <https://react.dev/>
2. Vite. <https://vitejs.dev/>
3. Three.js. <https://threejs.org/docs/>
4. Three.js `CSS2DRenderer` y `OrbitControls`.
5. MDN WebGL. <https://developer.mozilla.org/docs/Web/API/WebGL_API>
