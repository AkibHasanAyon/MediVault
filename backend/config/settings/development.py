"""
Development settings for MediVault.
"""
from .base import *

DEBUG = True

# Allow fallback SQLite database if PostgreSQL container is offline during local testing
if not env('DATABASE_URL', default='').startswith('sqlite'):
    import socket
    db_host = env('DB_HOST', default='localhost')
    db_port = env.int('DB_PORT', default=5432)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect((db_host, db_port))
        s.close()
    except Exception:
        # Fall back to SQLite locally so manage.py commands don't crash when docker is down
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }

