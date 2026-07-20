# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# WeNGO - Django (ASGI / Daphne + Channels) production-capable image
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm

# --- Python runtime behaviour -------------------------------------------------
# PYTHONUNBUFFERED   -> logs stream straight to Docker (no buffering)
# PYTHONDONTWRITEBYTECODE -> no .pyc clutter inside the container
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# --- System dependencies ------------------------------------------------------
# Build deps (compiling mysqlclient / cffi):
#   build-essential, pkg-config, default-libmysqlclient-dev, libffi-dev
# Runtime deps for WeasyPrint (PDF receipts): Pango + fonts + mime db
# netcat is used by the entrypoint to wait for MySQL.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        default-libmysqlclient-dev \
        libffi-dev \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libjpeg62-turbo \
        shared-mime-info \
        fonts-liberation \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Python dependencies (cached layer) --------------------------------------
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# --- Project source -----------------------------------------------------------
COPY . .

# --- Entrypoint: waits for DB, runs migrations, collects static --------------
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

EXPOSE 8000

# Default (production) command: serve HTTP + WebSockets via Daphne (ASGI).
# docker-compose overrides this with runserver for local development.
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "wengo.asgi:application"]
