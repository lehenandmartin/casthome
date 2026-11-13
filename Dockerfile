# --- frontend build ---------------------------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- runtime ----------------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    FRONTEND_DIST=/app/frontend/dist
WORKDIR /app/backend
COPY backend/pyproject.toml ./
COPY backend/casthome ./casthome
RUN pip install --no-cache-dir . && useradd --system --uid 1000 casthome && mkdir -p /data && chown casthome /data
COPY --from=frontend /src/frontend/dist /app/frontend/dist
USER casthome
VOLUME ["/data"]
EXPOSE 8080
CMD ["python", "-m", "casthome.main"]
