import os

from .base import *

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

_test_database_name = os.getenv("TEST_DATABASE_NAME")
if _test_database_name:
    DATABASES["default"].setdefault("TEST", {})["NAME"] = _test_database_name
