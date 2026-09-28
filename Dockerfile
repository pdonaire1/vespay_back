# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12

# ── Etapa base ──────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

# ── Etapa de build (resuelve e instala dependencias con uv) ─────────────
FROM base AS builder

# INSTALL_DEV=true incluye el grupo dev (debug_toolbar, django_extensions, etc.)
# para poder usar config.settings.development dentro del contenedor.
ARG INSTALL_DEV=false

COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen $([ "$INSTALL_DEV" = "true" ] || echo "--no-dev") --no-install-project

COPY . .

RUN uv sync --frozen $([ "$INSTALL_DEV" = "true" ] || echo "--no-dev")

# ── Etapa de runtime ────────────────────────────────────────────────────
FROM base AS runtime

RUN groupadd --system app && useradd --system --create-home --gid app app

COPY --from=builder --chown=app:app /app /app

RUN chown app:app /app

ENV PATH="/app/.venv/bin:$PATH"

COPY --chown=app:app docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER app

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
