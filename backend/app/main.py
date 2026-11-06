"""Aplicación FastAPI de la PTAR digital.

Ejecución
---------
    cd backend
    .venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --port 8000

Documentación interactiva: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.simulation.plant import VERSION_MODELO

RAIZ = Path(__file__).resolve().parents[2]
FRONTEND_DIST = RAIZ / "frontend" / "dist"

app = FastAPI(
    title="PTAR Digital · Gemelo de planta de tratamiento",
    description=(
        "Simulación de una planta de tratamiento de aguas residuales con "
        "tren A2O, modelo reducido de ASM1 y visualización 3D interactiva. "
        "Incluye balances de DBO5, DQO y SST, tren de lodos y digestión "
        "anaerobia con recuperación de biogás."
    ),
    version=VERSION_MODELO,
    docs_url="/docs",
    redoc_url="/redoc",
)

origenes = os.getenv("PTAR_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origenes],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Simulation-Cache", "X-Model-Version"],
)

app.include_router(router)


@app.get("/", include_in_schema=False)
def raiz():
    if FRONTEND_DIST.exists():
        return RedirectResponse(url="/app/", status_code=307)
    return {
        "servicio": "PTAR Digital",
        "version_modelo": VERSION_MODELO,
        "docs": "/docs",
        "endpoints": [
            "GET /api/salud",
            "GET /api/catalogo",
            "GET /api/presets",
            "POST /api/simulaciones",
        ],
    }


if FRONTEND_DIST.exists():
    app.mount("/app", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
