# StatEdge — single-image build: React frontend baked into the FastAPI app.

FROM node:24-alpine AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
# Same-origin: the SPA calls /api/v1/... on the host that serves it
ENV VITE_API_BASE=/
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend /fe/dist ./static

ENV PYTHONPATH=/app
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
