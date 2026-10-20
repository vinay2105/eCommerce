from os import getenv

from .base import *

DEBUG = env_bool("DJANGO_DEBUG", False)
if DEBUG:
    raise ImproperlyConfigured("DJANGO_DEBUG must be False in production.")

if not env_list("DJANGO_ALLOWED_HOSTS"):
    raise ImproperlyConfigured("Set DJANGO_ALLOWED_HOSTS for production.")

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
MAILERS = {
    "default": {
        **MAILERS["default"],
        "BACKEND": getenv(
            "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
        ),
    }
}
