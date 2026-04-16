# This Dockerfile builds a Python application using the Astral UV image as the base. It sets up a builder stage to
# install dependencies defined in the pyproject.toml and uv.lock files, using caching to speed up subsequent builds.

# --- Etapa de Builder ---
# Usamos la imagen oficial de uv basada en Alpine para mayor ligereza y velocidad
FROM astral/uv:python3.12-alpine AS builder

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-dev

# --- Etapa de Runtime ---
# Usamos una imagen ligera de Python 3.12 en Alpine para la ejecución final
FROM python:3.12-alpine AS runtime

WORKDIR /app

# Instalamos dependencias del sistema necesarias en runtime:
# - postgresql-client: Para herramientas de base de datos.
# - libpq: Librería esencial para que el adaptador de Postgres (psycopg) funcione.
# - gettext: Necesario para la compilación de mensajes de traducción (compilemessages).
# - curl: Para healthchecks o descargas rápidas.
RUN apk add --no-cache \
    postgresql-dev \
    postgresql-client \
    libpq \
    curl \
    gettext

# Instala uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copiamos el código fuente del proyecto
COPY . /app

COPY --from=builder /app/.venv /app/.venv

# Variables de entorno críticos para Django y Python
ENV DJANGO_SETTINGS_MODULE=config.settings \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/bin:/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv"

# Puertos y comandos por defecto (overridable por docker-compose)
EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
