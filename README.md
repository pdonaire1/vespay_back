# VesPay Backend

Backend de **VesPay**, la super-app de pagos multicanal para Venezuela y LATAM. Consolida en un único ecosistema moneda local (Pago Móvil, transferencias bancarias), plataformas internacionales y crypto (PayPal, Binance Pay, Zelle, tarjetas), pagos presenciales NFC contactless e integración a terceros (API REST/Webhooks + widget `vepay_js`).

## Stack

| Capa | Tecnología |
|------|------------|
| Lenguaje | Python 3.12+ |
| Framework | Django 5.x + Django REST Framework |
| Auth / registro | Djoser + SimpleJWT (JWT) |
| Base de datos | PostgreSQL (psycopg 3) |
| Cache / broker | Redis |
| Tiempo real | Django Channels (WebSockets) + Daphne |
| Tareas async | Celery + django-celery-beat |
| Encriptación | `cryptography` (AES-256-GCM) |
| Gestor de dependencias | `uv` |
| Lint / format | Ruff + pre-commit |
| Tests | pytest + pytest-django + factory-boy |

## Estructura del proyecto

```
vespay_back/
├── config/                 # Proyecto Django (settings, urls, asgi, wsgi, celery)
│   └── settings/           # base.py, development.py, production.py, test.py
├── apps/
│   ├── users/              # Custom User (email) + Djoser
│   ├── accounts/           # Cuentas de pago vinculadas (credenciales cifradas)
│   ├── payments/           # Abstract Factory de procesadores, transacciones, comisiones
│   ├── nfc/                # Flujo dual-token NFC + Consumer WebSocket
│   ├── widgets/            # Apps de terceros + webhooks
│   └── services/           # Servicios pagados (electricidad, agua, internet)
├── common/                 # Modelos base y utilidades (crypto AES-256-GCM)
├── llm_context/            # Documentación de dominio (no modificar)
├── Dockerfile              # Imagen de producción
├── docker-compose.yml      # PostgreSQL + Redis para desarrollo
├── docker-compose.prod.yml # Stack completo de producción
└── AGENTS.md               # Guía para agentes que trabajen en el repo
```

## Requisitos previos

- [uv](https://docs.astral.sh/uv/) (gestor de dependencias y Python)
- Docker + Docker Compose (para PostgreSQL/Redis en local o despliegue)
- Opcional: Python 3.12 local (uv lo gestiona automáticamente)

---

## Desarrollo local

### 1. Instalar dependencias

```bash
uv sync
```

Esto crea el entorno virtual `.venv` e instala las dependencias de runtime y desarrollo a partir de `uv.lock`.

### 2. Levantar servicios (PostgreSQL + Redis)

```bash
docker compose up -d
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
```

Genera la clave de encriptación de credenciales (obligatoria para vincular cuentas de pago):

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Pega el resultado en `VESPAY_ENCRYPTION_KEY` dentro de `.env`.

### 4. Migrar y arrancar

```bash
uv run python manage.py migrate
uv run python manage.py runserver
```

El servidor usa por defecto `config.settings.development` (DEBUG, correo por consola, Channels en memoria y Celery eager).

### 5. Crear un superusuario (acceso al admin)

```bash
# Interactivo:
uv run python manage.py createsuperuser

# No interactivo:
DJANGO_SUPERUSER_EMAIL=admin@example.com DJANGO_SUPERUSER_PASSWORD=MiPass123 \
  uv run python manage.py createsuperuser --noinput
```

Accede al panel de administración en <http://localhost:8000/admin/> con ese email y contraseña. El admin usa sesión (no JWT).

### Calidad y tests

```bash
uv run ruff check .          # lint
uv run ruff format .         # formato
uv run pytest                # tests
uv run pre-commit run --all-files
```

---

## Despliegue en producción

### 1. Variables de entorno (obligatorias)

Crea un `.env` en producción con al menos:

| Variable | Descripción |
|----------|-------------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` |
| `DJANGO_SECRET_KEY` | Clave secreta de Django (generar con `secrets.token_urlsafe(50)`) |
| `DJANGO_ALLOWED_HOSTS` | Dominios permitidos separados por coma |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` | Conexión a PostgreSQL |
| `REDIS_URL` | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis para Celery |
| `VESPAY_ENCRYPTION_KEY` | Clave AES-256-GCM en base64 |
| `DJANGO_SECURE_SSL_REDIRECT` | `True` detrás de un proxy TLS, `False` en pruebas |

### 2. Construir y desplegar el stack completo

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

Esto levanta: `web` (Daphne sirviendo HTTP + WebSockets en `:8000`), `worker` (Celery), `beat` (Celery Beat), `postgres` y `redis`. El contenedor `web` aplica migraciones y recolecta estáticos automáticamente en el arranque (`docker-entrypoint.sh`).

### 3. Procesos disponibles

La misma imagen (`Dockerfile`) sirve para todos los procesos; se diferencian por el `CMD`:

| Proceso | Comando |
|---------|---------|
| Web (HTTP + WS) | `daphne -b 0.0.0.0 -p 8000 config.asgi:application` |
| Worker Celery | `celery -A config worker -l info` |
| Beat (tareas periódicas) | `celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler` |

> El `Dockerfile` usa una build multi-etapa con `uv` y corre como usuario no privilegiado (`app`).

### 4. Crear un superusuario (Docker)

```bash
# Interactivo:
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# No interactivo:
docker compose -f docker-compose.prod.yml exec \
  -e DJANGO_SUPERUSER_EMAIL=admin@example.com \
  -e DJANGO_SUPERUSER_PASSWORD=MiPass123 \
  web python manage.py createsuperuser --noinput
```

### 5. Exponer al tráfico

Pon un proxy con terminación TLS (Nginx, Caddy, Traefik, ELB) delante del puerto `8000`. El `web` debe poder ser alcanzado tanto por HTTP como por WebSocket (`/ws/...`). Django ya está configurado con `SECURE_PROXY_SSL_HEADER` y redirección HTTPS.

---

## Endpoints principales (bajo `/api/v1/`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/users/` | Registro (Djoser) |
| POST | `/auth/jwt/create/` | Login (JWT) |
| POST | `/auth/jwt/refresh/` | Refrescar token |
| GET | `/auth/users/me/` | Usuario actual |
| GET/POST | `/accounts/` | Vincular / listar cuentas de pago |
| GET/POST | `/payments/transactions/` | Listar / crear transacciones |
| POST | `/nfc/payer-token` | Token efímero del pagador (NFC) |
| POST | `/nfc/payee-token` | Token de cobro del receptor (NFC) |
| POST | `/nfc/process-payment` | Procesar pago NFC |
| WS | `/ws/nfc/<session_id>/` | Streaming de estado en tiempo real |
| GET/POST | `/widgets/` | Apps de terceros (app_id/api_key) |
| GET | `/services/catalog/` | Catálogo de servicios pagados |
| GET/POST | `/services/subscriptions/` | Suscripciones de servicios |

## Documentación de la API (OpenAPI 3)

Generada con `drf-spectacular`:

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/schema/` | Schema OpenAPI 3 (YAML por defecto, JSON con `Accept: application/vnd.oai.openapi+json`) |
| GET | `/api/docs/` | Swagger UI (requiere autenticación: sesión de admin o JWT) |
| GET | `/api/redoc/` | ReDoc (requiere autenticación: sesión de admin o JWT) |

Para más detalle de dominio (Matchmaking, Fee Engine, flujo NFC), consulta `AGENTS.md` y `llm_context/`.
