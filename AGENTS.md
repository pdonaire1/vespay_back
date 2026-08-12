# AGENTS.md — VesPay Backend

Guía de contexto, convenciones y skills para agentes (humanos o IA) que trabajen en este repositorio. Léelo completo antes de tocar código.

## 1. Qué es VesPay

VesPay es una **super-app de pagos multicanal** para Venezuela y LATAM. Consolida en un único ecosistema:

- **Moneda local:** Pago Móvil (Bs.) y transferencias bancarias (detección automática por API).
- **Internacional / crypto:** Binance Pay, PayPal, Zelle y tarjetas de crédito/débito internacionales.
- **Pagos presenciales:** NFC contactless (protocolo de doble token).
- **Terceros:** API REST + Webhooks (estilo Stripe) y el widget web `vepay_js`.

Documentación fuente de dominio (obligatoria leer antes de modelar): `llm_context/PRD.md`, `llm_context/VesPay.md`, `llm_context/VesPayNFCFlow.md`.

## 2. Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Lenguaje | Python 3.12+ |
| Framework | Django 5.x + Django REST Framework (DRF) |
| Auth / registro | Djoser + `djangorestframework-simplejwt` (JWT) |
| Base de datos | PostgreSQL (psycopg 3) |
| Cache / broker | Redis (`django-redis`, `celery`, `channels-redis`) |
| Tiempo real | Django Channels (WebSockets) + Daphne |
| Tareas async | Celery (+ `django-celery-beat`) |
| Encriptación | `cryptography` (AES-256-GCM para credenciales de pago) |
| Config | `django-environ` (variables de entorno en `.env`) |
| Gestor de deps | `uv` (lockfile en `uv.lock`) |
| Lint / format | Ruff (reglas en `pyproject.toml`) |
| Git hooks | pre-commit |
| Tests | pytest + pytest-django + factory-boy |

## 3. Estructura del proyecto

```
vespay_back/
├── config/                     # Proyecto Django (settings, urls, asgi, wsgi, celery)
│   ├── settings/               # base.py, development.py, production.py, test.py
│   ├── urls.py
│   ├── asgi.py                 # Routing de Channels (WebSocket NFC)
│   ├── wsgi.py
│   └── celery.py
├── apps/                       # Aplicaciones de dominio
│   ├── users/                  # Custom User (email como username), Djoser
│   ├── accounts/               # Cuentas de pago vinculadas (credenciales cifradas)
│   ├── payments/               # Abstract Factory de procesadores, transacciones, comisiones
│   ├── nfc/                    # Flujo dual-token NFC + Consumer WebSocket
│   ├── widgets/                # Apps de terceros (app_id/api_key) + webhooks
│   └── services/               # Servicios pagados (electricidad, agua, internet)
├── common/                     # Código compartido (models abstractos, utilidades crypto)
├── manage.py
├── pyproject.toml              # Dependencias + config de ruff/pytest
├── .pre-commit-config.yaml
├── .env.example
├── docker-compose.yml          # PostgreSQL + Redis para desarrollo
└── llm_context/                # Documentación de dominio (NO modificar)
```

## 4. Convenciones de arquitectura

- **Patrón Abstract Factory** (obligatorio en `apps/payments/processors`): toda la lógica de pagos se expone mediante una única interfaz `Payment.create(method) -> IPaymentProcessor`. Cada pasarela (PayPal, Binance, Pago Móvil, Zelle) implementa `validate_credentials`, `execute` y `check_status`.
- **Custom User Model:** `AUTH_USER_MODEL = "users.User"`. El `username` es el email. Nunca referenciar `auth.User` directamente.
- **Modelo base compartido:** usar `common.models.TimeStampedModel` (created_at/updated_at) y `common.models.UUIDModel` (UUID pk) para todos los modelos de dominio.
- **Credenciales sensibles:** nunca almacenar API keys en texto plano. Usar `common.utils.crypto.encrypt_field`/`decrypt_field` (AES-256-GCM).
- **Moneda:** usar `Decimal` para montos (nunca `float`). Los montos viajan en la API en string para evitar pérdida de precisión.
- **Enums:** usar `models.TextChoices`/`IntegerChoices` (nunca strings sueltos) para métodos y estados de pago.
- **API versionada:** todo bajo `/api/v1/...`. Nuevas versiones crean nuevo módulo de urls.
- **Settings por entorno:** `DJANGO_SETTINGS_MODULE=config.settings.development` (o `.production`). Nunca hardcodear secretos.

## 5. Comandos

```bash
# Instalar (crea .venv automáticamente)
uv sync

# Servidor de desarrollo (usa settings development)
uv run python manage.py runserver

# Migraciones
uv run python manage.py makemigrations
uv run python manage.py migrate

# Lint / format
uv run ruff check .
uv run ruff format .

# Tests
uv run pytest

# Shell
uv run python manage.py shell_plus   # requiere ipython (dev)
```

## 6. Estilo de código (Ruff)

- Formato: `ruff format` (line-length 100).
- Reglas habilitadas: `E, F, W, I, N, UP, B, SIM, C4, TID` (ver `pyproject.toml`).
- Imports: ordenados con `isort` integrado, agrupados en stdlib / third-party / first-party.
- Prohibidos los comentarios triviales; documentar solo el "por qué", no el "qué".
- Nombres: modelos en singular (`LinkedAccount`, no `LinkedAccounts`); managers como `objects`.
- Type hints en firmas públicas de servicios/utilidades; docstrings solo donde aporten contexto de dominio.

## 7. Skills / reglas de dominio

1. **Matchmaking Engine** (`apps/payments/matchmaking.py`): al cobrar, extraer método preferido del receptor; si el emisor lo tiene activo, usar directo; si no, cruzar plataformas por frecuencia de uso; último recurso, pedir selección.
2. **Fee Engine** (`apps/payments/fees.py`): regla global (porcentaje + fijo) con override por `app_id` de tercero. Toda transacción calcula `fee` y `net_amount`.
3. **Flujo NFC dual-token** (`apps/nfc/`): `POST /nfc/payer-token`, `POST /nfc/payee-token`, `POST /nfc/process-payment`. Tokens efímeros HMAC-SHA256 con TTL de 120s. Confirmación por WebSocket `wss://.../nfc/{session_id}` con evento `PAYMENT_SUCCESS`.
4. **Autodetección de fondos:** workers Celery (polling + webhook listeners) detectan acreditaciones sin reportes manuales.
5. **Seguridad:** cifrado AES-256-GCM para credenciales; PCI-DSS para tarjetas; notificación WebSocket < 500 ms.

## 8. Workflow de un cambio típico

1. Leer la doc de dominio correspondiente en `llm_context/`.
2. Crear/editar el modelo en el app correcto (usar `common.models`).
3. `uv run python manage.py makemigrations && migrate`.
4. Añadir serializers/views/urls bajo `/api/v1/`.
5. Escribir tests con pytest + factory-boy.
6. `uv run ruff check . && uv run ruff format . && uv run pytest`.
7. Commit (pre-commit correrá los hooks automáticamente).

## 9. Anti-patterns prohibidos

- `from django.contrib.auth.models import User` (usar `get_user_model()`).
- `float` para dinero.
- Lógica de negocio en views; va en services/procesadores.
- Secretos o credenciales en el repositorio (ver `.env.example`).
- Migraciones escritas a mano (usar `makemigrations`).
- `print()` para debugging (usar logging o `breakpoint()`).
