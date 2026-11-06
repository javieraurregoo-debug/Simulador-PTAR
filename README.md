# PTAR Digital · Gemelo digital de una planta de tratamiento de aguas residuales

Aplicación docente e ingenieril que simula el tren completo de una PTAR
(pretratamiento, primario, reactor A2O, clarificador secundario, desinfección y
línea de lodos) y lo representa en una escena 3D interactiva.

El proyecto se organiza en cuatro fases:

| Fase | Contenido | Documento |
|---|---|---|
| 1 | Investigación de procesos y criterios de diseño | [`docs/01_procesos_ptar.md`](docs/01_procesos_ptar.md) |
| 2 | Arquitectura React + FastAPI | [`docs/02_arquitectura.md`](docs/02_arquitectura.md) |
| 3 | Modelado de DBO₅, DQO y SST | [`docs/03_modelos_dbo_dqo_sst.md`](docs/03_modelos_dbo_dqo_sst.md) |
| 4 | Visualización 3D con Three.js | [`docs/04_visualizacion_3d.md`](docs/04_visualizacion_3d.md) |

## Demo en línea

- **Aplicación:** <https://simulador-ptar.vercel.app>
- **API interactiva (Swagger):** <https://simulador-ptar.vercel.app/docs>
- **Repositorio:** <https://github.com/javieraurregoo-debug/Simulador-PTAR>

Desplegada en Vercel: FastAPI corre como función serverless y el frontend se
sirve como build estático. La primera simulación de una instancia en frío puede
tardar 20-30 s; las siguientes se atienden desde la caché LRU.

## 1. Funcionalidades

- **Simulación física y biológica** del tren de agua y del tren de lodos.
- **Fraccionamiento automático** de DBO₅/DQO/SST a las fracciones COD de ASM1.
- **Reactor A2O** con cinética de Monod, nitrificación, desnitrificación,
  hidrólisis y asimilación de fósforo.
- **Clarificador secundario** con curva de Vesilind y punto de estado.
- **Digestión anaerobia** con producción de biogás y cogeneración.
- **Balances de masa** de DQO y SST con cierre porcentual.
- **Cuatro escenarios** de arranque: municipal, lluvias, industrial láctea y
  pequeña comunidad.
- **Escena 3D** con 13 unidades, tuberías animadas, etiquetas, colores por
  calidad y fichas por equipo.
- **Pestañas de operación, efluente, lodos y modelo**, enlazables por hash.
- **API REST** documentada y caché LRU por hash de la petición.

## 2. Resultado del caso base

Escenario municipal, 9 000 m³/d:

| Parámetro | Afluente | Efluente | Remoción |
|---|---:|---:|---:|
| DBO₅ | 240 mg/L | 3,1 mg/L | 98,8 % |
| DQO | 455 mg/L | 35,6 mg/L | 92,3 % |
| SST | 230 mg/L | 7,5 mg/L | 96,8 % |
| N total | 49,6 mg/L | 13,2 mg/L | 73,8 % |
| P total | 5,0 mg/L | 4,43 mg/L | 13,2 % |

| Operación | Valor |
|---|---:|
| MLSS | 1 811 mg/L |
| SRT | 18,9 d |
| F/M | 0,129 kg DQO/(kg SSV·d) |
| OUR | 2 315 kg O₂/d |
| Aire de sopladores | 67 707 m³/d |
| Biogás | 596 m³/d |
| Energía eléctrica | 1 308 kWh/d |
| Autosuficiencia energética | 82,2 % |
| Cierre de DQO | 109,1 % |
| Cierre de SST | 100,3 % |

> El fósforo no cumple el límite de 2 mg/L porque el modelo no incluye EBPR ni
> precipitación química. Es una limitación documentada, no un error de cálculo.

## 3. Estructura

```
Corte_3/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI, CORS y estáticos
│   │   ├── schemas.py           # Validación Pydantic
│   │   ├── api/routes.py        # Endpoints y caché
│   │   └── simulation/
│   │       ├── constants.py     # Cinética y estequiometría
│   │       ├── streams.py       # Corrientes y propiedades
│   │       ├── quality.py       # DBO/DQO/SST y fraccionamiento
│   │       ├── units.py         # Pretratamiento, primario, desinfección
│   │       ├── biological.py    # ASM1 reducido + A2O
│   │       ├── sludge.py        # Espesador, digestor, deshidratación
│   │       └── plant.py         # Orquestación, KPIs y catálogo 3D
│   ├── tests/                   # 21 pruebas
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── three/PlantScene.js  # Escena Three.js
│   │   ├── components/
│   │   ├── hooks/useSimulation.js
│   │   ├── api/client.js
│   │   └── lib/format.js
│   ├── package.json
│   └── vite.config.js
├── docs/
└── README.md
```

## 4. Requisitos

- Python 3.11 o superior (probado con 3.12).
- Node.js 18 o superior (probado con 20.18.1).
- Windows, Linux o macOS. Los comandos de ejemplo usan PowerShell.

## 5. Instalación y ejecución

### 5.1 Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

En Linux/macOS:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API: <http://127.0.0.1:8000/api/salud> · Documentación: <http://127.0.0.1:8000/docs>

### 5.2 Frontend en desarrollo

```powershell
cd frontend
npm install
npm run dev
```

Abrir <http://127.0.0.1:5173>. Vite redirige `/api` al backend en el puerto
8000, por lo que no se necesita configurar CORS.

### 5.3 Build de producción

```powershell
cd frontend
npm run build
cd ..\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

FastAPI sirve el bundle en <http://127.0.0.1:8000/app/> y la API en `/api`.
Si se despliega el frontend por separado, definir `VITE_API_URL` con la URL del
backend antes de compilar.

### 5.4 Despliegue en Vercel

El proyecto ya está publicado en producción:

- Aplicación: <https://simulador-ptar.vercel.app>
- Documentación de la API: <https://simulador-ptar.vercel.app/docs>

`main.py` es el entrypoint que Vercel detecta como FastAPI, `requirements.txt`
contiene solo las dependencias de runtime y `vercel.json` define el build del
frontend y el límite de 60 s de la función. El archivo `.vercelignore` excluye
`.venv`, `node_modules`, `dist` y artefactos de prueba.

Para publicar cambios después de la primera vez:

```powershell
.\scripts\deploy_vercel.ps1
```

El script usa la sesión de `vercel login` o un token en `VERCEL_TOKEN`, sube el
código por la API oficial y espera a que el despliegue quede `READY`.

## 6. Pruebas

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Cobertura actual: 21 pruebas de fraccionamiento, conservación de masa,
eficiencias, simulación completa, cierre de balances y contrato de la API
(validación, presets, catálogo y caché HIT/MISS).

## 7. API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/salud` | Estado, versión y tamaño de caché |
| GET | `/api/catalogo` | Unidades 3D, ecuaciones, presets y límites |
| GET | `/api/presets` | Lista de escenarios |
| GET | `/api/presets/{id}` | Escenario completo |
| GET | `/api/ecuaciones` | Ecuaciones para la pestaña Modelo |
| POST | `/api/simulaciones` | Simula el tren completo |

La respuesta incluye `afluente`, `etapas`, `reactores`, `tren_lodos`,
`efluente`, `kpis`, `limites`, `balance`, `perfil`, `caracterizacion`,
`operacion_biologica`, `sedimentador_secundario` y `meta`.

Cabeceras de respuesta:

- `X-Simulation-Cache: HIT | MISS`
- `X-Model-Version: 1.0.0`

Ejemplo mínimo:

```powershell
$body = @{
  influente = @{ caudal_m3_d = 9000; dbo5_mg_l = 240; dqo_mg_l = 455; sst_mg_l = 230 }
  diseno    = @{}
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/simulaciones `
  -ContentType 'application/json' -Body $body
```

## 8. Decisiones técnicas destacadas

- **ASM1 reducido** con resolución cuasi-estacionaria de especies rápidas: alta
  estabilidad numérica y tiempos de 8–30 s por escenario.
- **LSODA serializado** con un lock: el integrador de SciPy no es reentrante y
  FastAPI atiende peticiones en un threadpool. La caché evita repetir cálculos.
- **Catálogo 3D en el backend**: una sola fuente de verdad para geometría,
  etiquetas y datos.
- **Three.js puro**, sin React Three Fiber ni librerías de gráficas, para
  controlar el ciclo de vida y reducir el bundle.
- **Etiquetas HTML** con `CSS2DRenderer` y ocultamiento por colisión a 5 Hz.
- **Fósforo simplificado**: se asimila en la biomasa; no hay EBPR ni coagulación.

## 9. Limitaciones

1. Régimen permanente: no hay picos horarios ni lluvia dinámica.
2. Mezcla completa ideal en cada zona; sin CFD ni cortocircuitos.
3. Sedimentador empírico calibrado, no bifásico.
4. Sin eliminación biológica mejorada de fósforo.
5. Geometría 3D simbólica, no a escala métrica ni BIM.
6. Constantes de ASM1/Metcalf & Eddy sin calibrar con una planta real.

## 10. Documentación adicional

- [`docs/01_procesos_ptar.md`](docs/01_procesos_ptar.md): procesos, criterios y
  problemas operativos.
- [`docs/02_arquitectura.md`](docs/02_arquitectura.md): stack, contrato HTTP,
  estado de React y despliegue.
- [`docs/03_modelos_dbo_dqo_sst.md`](docs/03_modelos_dbo_dqo_sst.md):
  ecuaciones, calibración, verificación y supuestos.
- [`docs/04_visualizacion_3d.md`](docs/04_visualizacion_3d.md): escena,
  interacción, rendimiento y accesibilidad.
