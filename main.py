"""Punto de entrada de la aplicación para Vercel.

Vercel detecta este archivo como entrypoint de FastAPI y expone la
instancia ``app`` como una función serverless. El paquete real vive en
``backend/app``; aquí solo se agrega ``backend`` al ``sys.path`` para que
los imports absolutos (``from app...``) sigan funcionando igual que en
local.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BACKEND = RAIZ / "backend"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.main import app  # noqa: E402

__all__ = ["app"]
