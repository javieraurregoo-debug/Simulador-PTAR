"""Endpoints REST de la PTAR digital."""

from __future__ import annotations

import json
from hashlib import sha256
from threading import Lock

from fastapi import APIRouter, HTTPException, Response

from app.schemas import LimitesIn, SimulacionIn
from app.simulation.plant import (
    CATALOGO,
    VERSION_MODELO,
    lista_presets,
    preset,
    simular_desde_parametros,
)

router = APIRouter(prefix="/api", tags=["PTAR"])

_CACHE: dict[str, dict] = {}
_ORDEN: list[str] = []
_CACHE_MAX = 24
_LOCK = Lock()


ECUACIONES = [
    {
        "id": "dqo",
        "nombre": "Demanda química de oxígeno",
        "expresion": "DQO = S_I + S_S + X_S + X_I + X_BH + X_BA",
        "descripcion": (
            "Suma de las fracciones de COD del modelo ASM1: inerte soluble, "
            "sustrato soluble, sustrato particulado, inerte particulado y "
            "biomasa heterótrofa y autótrofa."
        ),
        "unidad": "mg/L",
        "variables": {
            "S_I": "COD soluble inerte",
            "S_S": "COD soluble fácilmente biodegradable",
            "X_S": "COD particulado lentamente biodegradable",
            "X_I": "COD particulado inerte",
            "X_BH": "biomasa heterótrofa",
            "X_BA": "biomasa autótrofa",
        },
    },
    {
        "id": "dbo5",
        "nombre": "Demanda bioquímica de oxígeno a 5 días",
        "expresion": "DBO5 = f_BOD · (S_S + X_S + X_BH + X_BA)",
        "descripcion": (
            "La DBO5 se estima a partir del COD biodegradable con "
            "f_BOD = 0,65 g DBO5/g COD. Para agua municipal reproduce la "
            "relación típica DBO5/DQO ≈ 0,5."
        ),
        "unidad": "mg/L",
        "variables": {"f_BOD": "0,65 g DBO5/g COD biodegradable"},
    },
    {
        "id": "sst",
        "nombre": "Sólidos suspendidos totales",
        "expresion": "SST = ISS + (X_S + X_I + X_BH + X_BA) / i_COD_SST",
        "descripcion": (
            "Los sólidos se obtienen del COD particulado con i_COD_SST = 1,14 "
            "g COD/g SST, más los sólidos inorgánicos ISS."
        ),
        "unidad": "mg/L",
        "variables": {"ISS": "sólidos inorgánicos", "i_COD_SST": "1,14 g COD/g SST"},
    },
    {
        "id": "monod",
        "nombre": "Crecimiento bacteriano (Monod)",
        "expresion": "μ = μ_max · S/(K_S + S) · O2/(K_O2 + O2)",
        "descripcion": (
            "Cinética de crecimiento limitada por sustrato y oxígeno. En la "
            "zona anóxica se usa NO3 como aceptor de electrones."
        ),
        "unidad": "1/d",
    },
    {
        "id": "srt",
        "nombre": "Tiempo de retención de sólidos",
        "expresion": "SRT = (X · V) / (Q_w · X_r + Q_e · X_e)",
        "descripcion": (
            "Relaciona la masa de lodos en el reactor con la masa purgada y "
            "la que escapa por el efluente. Controla la nitrificación y la "
            "edad del lodo."
        ),
        "unidad": "d",
    },
    {
        "id": "fm",
        "nombre": "Relación alimento/microorganismo",
        "expresion": "F/M = (Q · S_0) / (V · X_VSS)",
        "descripcion": "Carga orgánica por unidad de biomasa activa.",
        "unidad": "kg DQO/(kg SSV·d)",
    },
    {
        "id": "our",
        "nombre": "Consumo de oxígeno",
        "expresion": "OUR = (1−Y_H)/Y_H · μ_H·X_BH + (4,57−Y_A)/Y_A · μ_A·X_BA",
        "descripcion": (
            "Oxígeno requerido para oxidar el sustrato y nitrificar. Se "
            "corrige por transferencia con los factores α y β."
        ),
        "unidad": "kg O2/d",
    },
    {
        "id": "hazen",
        "nombre": "Sedimentación primaria (Hazen)",
        "expresion": "η(v_s) = 1 − (1 + v_s/(v_c·N))^(−N)",
        "descripcion": (
            "Eficiencia de captura integrada sobre una distribución lognormal "
            "de velocidades de sedimentación, corregida por dispersión "
            "hidráulica (N reactores en serie)."
        ),
        "unidad": "%",
    },
    {
        "id": "vesilind",
        "nombre": "Flujo de sólidos del clarificador (Vesilind)",
        "expresion": "G = X · (V_0·e^(−K·X) + u),  u = Q_sub/A",
        "descripcion": (
            "El punto de estado compara la carga de sólidos aplicada con la "
            "capacidad de la curva de flujo. Si G_aplicado > G_límite el manto "
            "asciende y se produce arrastre de sólidos."
        ),
        "unidad": "kg/(m²·h)",
    },
    {
        "id": "chick",
        "nombre": "Desinfección (Chick-Watson)",
        "expresion": "log10(N/N0) = −k · C^n · t · f_T · f_pH",
        "descripcion": (
            "Inactivación de coliformes por cloro libre. Para UV se usa "
            "log10(N/N0) = −D/D90 y para ozono un CT equivalente."
        ),
        "unidad": "log",
    },
    {
        "id": "balance",
        "nombre": "Balance de masa",
        "expresion": "Σ Q_e·C_e = Σ Q_i·C_i + r·V",
        "descripcion": (
            "Cierre de DQO y SST sobre todo el tren, incluyendo lodos, "
            "biogás, oxidación biológica y residuos de pretratamiento. Un "
            "cierre entre 85 % y 115 % se considera aceptable."
        ),
        "unidad": "kg/d",
    },
]


def _clave(payload: dict) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def ejecutar(payload: dict) -> tuple[dict, bool]:
    """Ejecuta la simulación con caché LRU en memoria."""
    clave = _clave(payload)
    with _LOCK:
        if clave in _CACHE:
            return _CACHE[clave], True

    resultado = simular_desde_parametros(payload)

    with _LOCK:
        _CACHE[clave] = resultado
        _ORDEN.append(clave)
        while len(_ORDEN) > _CACHE_MAX:
            viejo = _ORDEN.pop(0)
            _CACHE.pop(viejo, None)
    return resultado, False


@router.get("/salud", summary="Estado del servicio")
def salud() -> dict:
    return {
        "estado": "ok",
        "version_modelo": VERSION_MODELO,
        "simulaciones_en_cache": len(_CACHE),
    }


@router.get("/catalogo", summary="Catálogo de unidades, ecuaciones y presets")
def catalogo() -> dict:
    return {
        "unidades": CATALOGO,
        "ecuaciones": ECUACIONES,
        "presets": lista_presets(),
        "limites_default": LimitesIn().model_dump(),
        "influente_default": {
            "caudal_m3_d": 9000.0,
            "dbo5_mg_l": 240.0,
            "dqo_mg_l": 455.0,
            "sst_mg_l": 230.0,
            "ssv_mg_l": 185.0,
            "ntk_mg_l": 42.0,
            "nh4_mg_l": 32.0,
            "no3_mg_l": 0.0,
            "pt_mg_l": 7.0,
            "po4_mg_l": 5.0,
            "alcalinidad_mg_l": 260.0,
            "ph": 7.2,
            "temperatura_c": 22.0,
            "coliformes_ufc_100ml": 2.5e7,
            "turbiedad_ntu": 180.0,
        },
        "unidades_medida": {
            "caudal": "m³/d",
            "concentracion": "mg/L",
            "carga": "kg/d",
            "energia": "kWh/d",
        },
    }


@router.get("/presets", summary="Lista de escenarios de arranque")
def presets() -> list[dict]:
    return lista_presets()


@router.get("/presets/{preset_id}", summary="Escenario completo")
def obtener_preset(preset_id: str) -> dict:
    try:
        return preset(preset_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"El preset '{preset_id}' no existe.",
        ) from exc


@router.get("/ecuaciones", summary="Ecuaciones del modelo")
def ecuaciones() -> list[dict]:
    return ECUACIONES


@router.post("/simulaciones", summary="Simula el tren completo de la PTAR")
def simular(payload: SimulacionIn, response: Response) -> dict:
    datos = payload.model_dump()
    try:
        resultado, cache = ejecutar(datos)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response.headers["X-Simulation-Cache"] = "HIT" if cache else "MISS"
    response.headers["X-Model-Version"] = VERSION_MODELO
    return resultado
