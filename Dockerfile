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
RUN pip install --no-cache-dir . && mkdir -p /data
COPY --from=frontend /src/frontend/dist /app/frontend/dist
COPY docker/entrypoint.sh /usr/local/bin/casthome-entrypoint
# The entrypoint fixes the owner of /data (a mounted folder is often root's),
# then drops to PUID:PGID (default 1000:1000) to run CastHome.
ENV PUID=1000 PGID=1000
VOLUME ["/data"]
EXPOSE 8080
ENTRYPOINT ["casthome-entrypoint"]
CMD ["python", "-m", "casthome.main"]
