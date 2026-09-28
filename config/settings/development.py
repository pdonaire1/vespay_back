from .base import *  # noqa: F403
from .base import INSTALLED_APPS, MIDDLEWARE, REST_FRAMEWORK, env

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS += ["django_extensions", "debug_toolbar"]

MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware", *MIDDLEWARE]

INTERNAL_IPS = ["127.0.0.1", "localhost"]


# En desarrollo el backend de canales in-memory evita depender de Redis para WS
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Por defecto las tareas se encolan en Redis y las procesa el worker de docker-compose.
# Para desarrollo local sin worker/Redis: CELERY_TASK_ALWAYS_EAGER=True en .env.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)

DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda _request: DEBUG}

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
}

# Dev: el cliente Flutter (web/desktop) usa puertos aleatorios — permitir todos los origenes.
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True


# Cache en memoria para desarrollo (no requiere Redis local).
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
