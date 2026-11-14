# --- frontend build ---------------------------------------------------------
# The built files do not depend on the CPU: build them natively, not emulated.
FROM --platform=$BUILDPLATFORM node:22-alpine AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- runtime ----------------------------------------------------------------
FROM python:3.12-slim
LABEL org.opencontainers.image.source="https://github.com/lehenandmartin/casthome" \
      org.opencontainers.image.description="Navidrome to Google Cast web player" \
      org.opencontainers.image.licenses="MIT"
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
# Commit the image was built from, shown in Settings next to the version.
ARG REVISION=""
ENV CASTHOME_REVISION=$REVISION
VOLUME ["/data"]
EXPOSE 4577
ENTRYPOINT ["casthome-entrypoint"]
CMD ["python", "-m", "casthome.main"]
