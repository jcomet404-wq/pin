"""FastAPI app powering the PIN web map."""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pin.web.render import available_styles, render_index, render_legend

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="PIN — Planetary Intelligence Network", version="0.1.0")

# Allow a statically-hosted frontend (e.g. Vercel) to call this backend.
# Set PIN_CORS_ORIGINS to a comma-separated list of origins; defaults to "*".
_origins = [o.strip() for o in os.environ.get("PIN_CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ComputeRequest(BaseModel):
    index: str
    bbox: list[float] = Field(..., min_length=4, max_length=4)
    datetime: str
    resolution: float = 60.0
    max_cloud_cover: float = 30.0
    iso3: str | None = None
    year: int | None = None


@app.get("/api/styles")
def get_styles() -> dict[str, dict[str, object]]:
    return available_styles()


@app.get("/api/legend/{index}")
def get_legend(index: str) -> Response:
    try:
        png = render_legend(index)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=png, media_type="image/png")


@app.post("/api/compute")
def compute(req: ComputeRequest) -> dict:
    try:
        result = render_index(
            req.index,
            req.bbox,
            req.datetime,
            resolution=req.resolution,
            max_cloud_cover=req.max_cloud_cover,
            iso3=req.iso3,
            year=req.year,
        )
    except (LookupError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("compute failed")
        raise HTTPException(status_code=500, detail=f"Failed to compute: {exc}") from exc

    b64 = base64.b64encode(result.pop("png")).decode("ascii")
    result["image"] = f"data:image/png;base64,{b64}"
    return result


# Serve the frontend at the root (index.html + relative assets). Mounted after
# the API routes so /api/* still resolves. Assets use relative paths so the same
# files also work when hosted statically (e.g. on Vercel).
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)
