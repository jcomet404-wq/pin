# PIN compute backend (FastAPI). Deploy to any container host (Fly.io, Render,
# Railway, Cloud Run, a VM, ...). The frontend can be served by this same
# container, or hosted separately (e.g. Vercel) pointing at this backend.
FROM python:3.11-slim

WORKDIR /app

# rasterio/rioxarray/odc-stac ship manylinux wheels, so no system GDAL needed.
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir ".[web]"

# Lock down CORS in production by overriding this (comma-separated origins),
# e.g. PIN_CORS_ORIGINS=https://your-frontend.vercel.app
ENV PIN_CORS_ORIGINS="*"

EXPOSE 8000

# Hosts inject $PORT (Fly/Render/Railway/Cloud Run); default to 8000 locally.
CMD ["sh", "-c", "uvicorn pin.web.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
