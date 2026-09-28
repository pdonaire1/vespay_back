from .base import *  # noqa: F403

DEBUG = False

# SQLite en memoria para velocidad en CI/local; PostgreSQL en otros entornos.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Clave AES determinista para tests (no requiere .env).
VESPAY_ENCRYPTION_KEY = "dmVzcGF5LXRlc3Qta2V5LTEyMzQ1Njc4OTBhYmNkZWY="

CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Cache en memoria: aísla los tests entre ejecuciones (no comparte Redis).
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

CELERY_TASK_ALWAYS_EAGER = True
