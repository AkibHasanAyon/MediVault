"""
Development settings for MediVault.
"""
import sys
import socket
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# Allow fallback SQLite database if PostgreSQL container is offline during local testing
if not env('DATABASE_URL', default='').startswith('sqlite'):
    db_host = env('DB_HOST', default='localhost')
    db_port = env.int('DB_PORT', default=5432)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
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

# Celery & Channels configuration for testing and offline development
is_testing = 'pytest' in sys.modules or any('pytest' in arg for arg in sys.argv) or 'test' in sys.argv

redis_available = False
if not is_testing:
    try:
        s_redis = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s_redis.settimeout(0.2)
        s_redis.connect(('localhost', 6379))
        s_redis.close()
        redis_available = True
    except Exception:
        redis_available = False

if is_testing or not redis_available:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }
