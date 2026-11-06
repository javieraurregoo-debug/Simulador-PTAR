# Backend · PTAR Digital

API FastAPI y motor de simulación del tren completo de una planta de tratamiento
de aguas residuales. El paquete `app.simulation` no depende de FastAPI: puede
usarse desde scripts, cuadernos o pruebas.

## 1. Requisitos

- Python 3.11+ (probado con 3.12)
- FastAPI 0.115, Pydantic 2.10, NumPy 2.2, SciPy 1.15
- Uvicorn, Pytest y HTTPX

## 2. Instalación

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Ejecución

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- API: <http://127.0.0.1:8000/api/salud>
- Swagger: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- Interfaz compilada: <http://127.0.0.1:8000/app/> (si existe `frontend/dist`)

Para producción:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Variables de entorno:

| Variable | Efecto | Valor por defecto |
|---|---|---|
| `PTAR_CORS_ORIGINS` | Orígenes permitidos, separados por coma | `*` |

## 4. Estructura

```
backend/
├── app/
│   ├── main.py                 # App FastAPI, CORS y montaje de /app
│   ├── schemas.py              # Entrada validada con Pydantic
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # Endpoints, ecuaciones y caché LRU
│   └── simulation/
│       ├── constants.py        # Constantes cinéticas y estequiométricas
│       ├── streams.py          # Clase Stream y propiedades
│       ├── quality.py          # Fraccionamiento y calidad del agua
│       ├── units.py            # Rejillas, desarenador, primario, desinfección
│       ├── biological.py       # ASM1 reducido, A2O y clarificador
│       ├── sludge.py           # Espesador, digestor y deshidratación
│       └── plant.py            # Orquestación, catálogo 3D, KPIs y presets
├── tests/
│   ├── conftest.py
│   ├── test_quality.py
│   ├── test_plant.py
│   └── test_api.py
└── requirements.txt
```

## 5. Flujo de simulación

```
POST /api/simulaciones
        │
        ▼
SimulacionIn (Pydantic)
        │
        ▼
fraccionar_influente()  ── DBO5/DQO/SST → S_I, S_S, X_S, X_I, ISS…
        │
        ▼
simular_planta()
   ├── rejillas + desarenador
   ├── sedimentador primario
   ├── reactor A2O (anaerobio → anóxico → aerobio)
   ├── sedimentador secundario (Vesilind)
   ├── desinfección (cloro, UV u ozono)
   ├── tren de lodos (espesador → digestor → deshidratación)
   └── balances, límites, KPIs y perfil
        │
        ▼
JSON + cabeceras X-Simulation-Cache / X-Model-Version
```

Cada etapa devuelve entrada, salida, remociones e indicadores de diseño. El
resultado es autocontenido: el frontend no recalcula nada.

## 6. Endpoints

| Método | Ruta | Respuesta |
|---|---|---|
| GET | `/api/salud` | Estado, versión y entradas en caché |
| GET | `/api/catalogo` | Unidades, ecuaciones, presets y límites |
| GET | `/api/presets` | Resumen de los cuatro escenarios |
| GET | `/api/presets/{id}` | Escenario completo |
| GET | `/api/ecuaciones` | Ecuaciones del modelo |
| POST | `/api/simulaciones` | Simulación completa |

### 6.1 Petición

```json
{
  "influente": {
    "caudal_m3_d": 9000,
    "dbo5_mg_l": 240,
    "dqo_mg_l": 455,
    "sst_mg_l": 230,
    "ssv_mg_l": 185,
    "ntk_mg_l": 42,
    "nh4_mg_l": 32,
    "pt_mg_l": 7,
    "po4_mg_l": 5,
    "temperatura_c": 22
  },
  "diseno": {
    "biologico": {
      "volumen_anaerobio_m3": 900,
      "volumen_anoxico_m3": 1800,
      "volumen_aerobio_m3": 5400,
      "ras": 0.8,
      "recirculacion_interna": 3.0,
      "purga_m3_d": 180,
      "svi_ml_g": 140
    },
    "desinfeccion": { "metodo": "cloro", "dosis_cloro_mg_l": 4 }
  },
  "limites": {
    "dbo5_mg_l": 50,
    "dqo_mg_l": 150,
    "sst_mg_l": 50,
    "nt_mg_l": 15,
    "pt_mg_l": 2
  }
}
```

Todos los campos de `diseno` y `limites` tienen valores por defecto. Las
validaciones principales son:

- `0 < caudal_m3_d ≤ 2·10⁶`.
- `DBO5 < DQO`.
- `SSV ≤ SST`.
- `NH4 ≤ NTK`.
- `0,1 ≤ RAS ≤ 3`; `0 ≤ recirculación interna ≤ 6`.
- `30 ≤ dias_simulacion ≤ 365`.
- Método de desinfección: `cloro`, `uv`, `ozono` o `ninguno`.

Una violación devuelve `422` con el detalle del campo.

### 6.2 Respuesta (resumen)

```json
{
  "afluente": { "dqo_mg_l": 455, "dbo5_mg_l": 240, "sst_mg_l": 230 },
  "etapas": [],
  "reactores": [],
  "tren_lodos": { "etapas": [], "resumen": {} },
  "efluente": { "dbo5_mg_l": 3.1, "dqo_mg_l": 35.6, "sst_mg_l": 7.5 },
  "kpis": {},
  "limites": { "cumple_global": false },
  "balance": {},
  "perfil": [],
  "caracterizacion": {},
  "operacion_biologica": {},
  "sedimentador_secundario": {},
  "meta": { "version_modelo": "1.0.0" }
}
```

Cabeceras:

- `X-Simulation-Cache`: `HIT` si la petición estaba en caché, `MISS` si se
  ejecutó.
- `X-Model-Version`: versión del modelo (`1.0.0`).

La caché es un LRU en memoria de 24 escenarios, indexado por SHA-256 del JSON
canónico. Se reinicia con el proceso.

## 7. Modelo

- **Fraccionamiento:** `S_I = 0,06·DQO`, `bCOD = DBO5/0,65`,
  `X_I = DQO − S_I − bCOD`, `X_S` acotado y `S_S` por diferencia.
- **Reactor A2O:** 5 variables lentas por zona (`S_I`, `X_BH`, `X_BA`, `X_I`,
  `ISS`); especies rápidas en estado cuasi-estacionario.
- **Integración:** `solve_ivp` (LSODA), 180 d en 6 bloques, `rtol=1e-6`,
  `atol=1e-3`, paso máximo 5 d.
- **Clarificador:** curva de Vesilind y punto de estado; se impone un rebose
  mínimo de sólidos no sedimentables.
- **Lodos:** espesamiento, digestión anaerobia, biogás con 63 % de CH₄ y
  cogeneración con 35 % de eficiencia eléctrica.
- **Balances:** DQO y SST con cierre porcentual; se incluyen oxidación
  biológica, biogás, residuos de pretratamiento y torta.

Detalle completo en [`../docs/03_modelos_dbo_dqo_sst.md`](../docs/03_modelos_dbo_dqo_sst.md).

### 7.1 Concurrencia

El integrador LSODA de SciPy **no es reentrante**. FastAPI ejecuta los endpoints
síncronos en un threadpool, así que dos simulaciones simultáneas pueden lanzar
`IntegratorConcurrencyError`. `biological.py` protege la integración con un
`threading.Lock`; el resto del cálculo y la serialización siguen en paralelo.
La caché LRU hace que repetir un escenario sea instantáneo. Si se despliega con
varios workers, cada proceso tiene su propio lock y su propia caché.

## 8. Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Resultado esperado: **21 passed**.

| Archivo | Cobertura |
|---|---|
| `test_quality.py` | Fraccionamiento, DBO/DQO/SST, conservación, eficiencias |
| `test_plant.py` | Simulación municipal, cierre de balances, convergencia |
| `test_api.py` | Catálogo, presets, validación 422, caché HIT/MISS |

Prueba rápida de humo:

```powershell
$p = Invoke-RestMethod http://127.0.0.1:8000/api/presets/municipal
$body = @{ influente = $p.influente; diseno = $p.diseno } | ConvertTo-Json -Depth 10
$r = Invoke-WebRequest -UseBasicParsing -Method Post `
  -Uri http://127.0.0.1:8000/api/simulaciones `
  -ContentType 'application/json' -Body $body
($r.Content | ConvertFrom-Json).efluente
```

## 9. Rendimiento

| Escenario | Tiempo típico |
|---|---:|
| Primera simulación (MISS) | 8–30 s según equipo y carga |
| Repetición exacta (HIT) | < 50 ms |
| Llamadas concurrentes | Serializadas en la integración; el resto en paralelo |

Para reducir el tiempo: bajar `dias_simulacion` (mínimo 30), simplificar el
diseño o mantener la caché caliente. No se recomienda aumentar `rtol`/`atol` sin
revisar la convergencia.

## 10. Solución de problemas

| Síntoma | Causa probable | Acción |
|---|---|---|
| `ModuleNotFoundError: app` | Se ejecutó Uvicorn fuera de `backend/` | `cd backend` antes de iniciar |
| `422` con «La DBO5 debe ser menor que la DQO» | Caracterización incoherente | Corregir DBO5 o DQO |
| `500 IntegratorConcurrencyError` | Versión antigua sin lock | Actualizar `biological.py` y reiniciar |
| `404` en `/app/` | No existe `frontend/dist` | `npm run build` en `frontend/` |
| La simulación tarda demasiado | Caché fría o `dias_simulacion` alto | Repetir el escenario o reducir días |
| El puerto 8000 está ocupado | Otro Uvicorn activo | Cambiar `--port` o detener el proceso |

## 11. Referencias

1. Henze, M. et al. (1987). *Activated Sludge Model No. 1*. IAWPRC.
2. Metcalf & Eddy (2014). *Wastewater Engineering*, 5th ed.
3. Vesilind, P.A. (1968). Design of prototype thickeners from batch settling
   tests. *Water & Sewage Works*, 115.
4. FastAPI Documentation. <https://fastapi.tiangolo.com/>
5. SciPy `solve_ivp`. <https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html>
