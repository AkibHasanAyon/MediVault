# MediVault — Clinical Debugging & Troubleshooting Handbook

> **Target Systems:** Django REST Framework, Daphne ASGI, Celery Workers, Redis, ChromaDB, Google Cloud Vision, OpenAI API  
> **Development Context:** Windows PowerShell, Docker Desktop, Linux Staging

---

## 1. Local Debugging Environment Configuration

### 1.1 VS Code Launch Configuration (`.vscode/launch.json`)

To debug Django API, Celery workers, and Daphne ASGI processes directly in VS Code:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Django: Runserver (ASGI)",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/backend/manage.py",
      "args": ["runserver", "8000"],
      "django": true,
      "justMyCode": true,
      "env": {
        "DJANGO_SETTINGS_MODULE": "config.settings.development"
      }
    },
    {
      "name": "Celery: Worker",
      "type": "debugpy",
      "request": "launch",
      "module": "celery",
      "args": [
        "-A", "config",
        "worker",
        "-l", "DEBUG",
        "-P", "solo"
      ],
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "DJANGO_SETTINGS_MODULE": "config.settings.development"
      }
    },
    {
      "name": "Celery: Beat",
      "type": "debugpy",
      "request": "launch",
      "module": "celery",
      "args": [
        "-A", "config",
        "beat",
        "-l", "DEBUG"
      ],
      "cwd": "${workspaceFolder}/backend"
    }
  ]
}
```

> [!NOTE]
> On **Windows**, Celery worker requires `-P solo` or `--pool=gevent` because standard prefork pooling is unsupported by Windows process spawning.

---

## 2. Structured Django Logging Configuration

Add to `config/settings/base.py` for comprehensive file and console logging:

```python
import os

LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file_django': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django_errors.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_ai': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'ai_pipeline.log'),
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_django'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps.ai_services': {
            'handlers': ['console', 'file_ai'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'apps.documents': {
            'handlers': ['console', 'file_ai'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

---

## 3. Celery & Asynchronous Task Debugging

### 3.1 Inspecting Active and Pending Tasks
Run these commands from the `backend/` directory with virtual environment active:

```bash
# View active worker nodes
celery -A config status

# Inspect currently executing tasks
celery -A config inspect active

# Inspect scheduled / delayed tasks (e.g. OCR retries)
celery -A config inspect scheduled

# Purge all pending tasks from Redis (Emergency queue reset)
celery -A config purge -f
```

### 3.2 Debugging Failed Tasks Locally
To run a Celery task synchronously in your terminal for immediate step-through debugging:

```python
# Open Django enhanced shell
python manage.py shell_plus

# Run task directly in the foreground without Celery worker
from apps.documents.tasks import process_document_ocr_task
result = process_document_ocr_task("7c1b5049-e314-411a-a128-4f24f5a2b160")
print(result)
```

---

## 4. WebSocket (Django Channels) Debugging

### 4.1 Testing WebSocket Connections with `wscat`
Install `wscat` globally via npm:
```bash
npm install -g wscat
```

Connect directly to the clinic queue feed:
```bash
# Connect to Clinic Queue with JWT Token
wscat -c "ws://localhost:8000/ws/queue/5/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

If successful, you will see `Connected (press CTRL+C to quit)`. When an assistant marks a patient called-in, you should receive:
```json
{"type": "queue.update", "payload": {"current_token_in_chamber": 14}}
```

### 4.2 Inspecting Redis Channel Layer
To verify Redis is receiving channel group messages:
```bash
# In another terminal
docker exec -it medivault-redis-1 redis-cli

# Subscribe to all Channel events
PSUBSCRIBE *
```

---

## 5. Custom Diagnostic Management Commands

Place these in `apps/common/management/commands/` for instant operational verification:

### 5.1 Test Google Cloud Vision (`test_ocr.py`)
```python
from django.core.management.base import BaseCommand
from apps.ai_services.ocr_service import OCRService

class Command(BaseCommand):
    help = "Tests Google Cloud Vision OCR against a local image file"

    def add_arguments(self, parser):
        parser.add_argument('image_path', type=str)

    def handle(self, *args, **options):
        self.stdout.write("Connecting to Google Cloud Vision...")
        ocr = OCRService()
        res = ocr.extract_text(options['image_path'])
        self.stdout.write(self.style.SUCCESS(f"OCR Success (Confidence: {res.confidence})"))
        self.stdout.write(f"Raw Text Extracted:\n{res.raw_text[:500]}...")
```

### 5.2 Test OpenAI & ChromaDB (`test_ai.py`)
```python
from django.core.management.base import BaseCommand
from apps.ai_services.openai_service import OpenAIService
from apps.ai_services.chroma_service import ChromaService

class Command(BaseCommand):
    help = "Tests OpenAI connection and ChromaDB vector search"

    def handle(self, *args, **options):
        self.stdout.write("1. Testing OpenAI Embedding...")
        ai = OpenAIService()
        vec = ai.get_embedding("Test medical string: Tab. Metformin 500mg")
        self.stdout.write(self.style.SUCCESS(f"Generated 1536d vector (Length: {len(vec)})"))

        self.stdout.write("2. Testing ChromaDB Connection...")
        chroma = ChromaService()
        chroma.index_document("test_01", "patient_99", "Tab. Metformin 500mg", {"type": "PRESCRIPTION"})
        results = chroma.search_patient_documents("patient_99", "What diabetes medication?")
        self.stdout.write(self.style.SUCCESS(f"ChromaDB Query Result: {results}"))
```

---

## 6. Diagnostic Cheatsheet: 30+ Common Symptoms & Solutions

| Category | Observed Symptom | Likely Root Cause | Exact Resolution |
|---|---|---|---|
| **Auth** | `401 Unauthorized` with valid token | Token expired or clock skew between host and container | Run `w32tm /resync` on Windows host or check `ACCESS_TOKEN_LIFETIME` in settings. |
| **Auth** | `403 Forbidden` on Doctor endpoints | Logged-in user has role `PATIENT` instead of `DOCTOR` | Check `request.user.role`. Verify role selection during registration. |
| **Auth** | `Token is blacklisted` | User logged out or refresh token was rotated | Client must perform fresh login via `POST /api/v1/auth/login/`. |
| **OCR** | `GCP Vision Error: 403 Permission Denied` | Cloud Vision API not enabled or credentials invalid | Go to GCP Console → Enable "Cloud Vision API". Verify `GOOGLE_APPLICATION_CREDENTIALS` path. |
| **OCR** | `Document status stuck on PENDING` | Celery worker is not running or Redis is unreachable | Check `docker ps` for `celery_worker` container. Verify Redis port 6379 is listening. |
| **OCR** | Low extraction accuracy on phone photos | Low contrast or blue ballpoint pen on colored paper | Ensure `preprocess_image` applies contrast enhancement filter before calling GCP. |
| **AI** | `OpenAI Error: 429 Rate Limit Exceeded` | Tier 1 organization quota or missing payment method | Check OpenAI billing tier. Implement exponential backoff in `OpenAIService`. |
| **AI** | `JSONDecodeError` during entity extraction | GPT-4o-mini produced non-JSON markdown tags | Add `response_format={"type": "json_object"}` in `chat.completions.create`. |
| **AI** | `ChromaDB: Connection refused (port 8000)` | Chroma container stopped or listening on localhost inside Docker | In Docker network, use `CHROMA_HOST=chromadb` instead of `localhost`. |
| **Vitals** | Danger alert did not fire on glucose 3.4 | Reading value saved as string instead of Decimal | Ensure serializer uses `serializers.DecimalField(max_digits=4, decimal_places=1)`. |
| **Queue** | WebSocket connects then immediately closes | Missing or invalid JWT token in connection query param | Pass token via query param `?token=...` and verify `AuthMiddlewareStack` handles it. |
| **Queue** | Doctor doesn't receive real-time queue shift | Assistant and Doctor connected to different clinic IDs | Verify WebSocket URL has matching `clinic_id` UUID in route kwargs. |
| **DB** | `django.db.utils.OperationalError: connection refused` | PostgreSQL container is starting up or port 5432 is busy | Wait 5 seconds for healthcheck. Check for native PostgreSQL service conflicting on 5432. |
| **DB** | `InconsistentMigrationHistory` | Migrations applied out of order or branch mismatch | Run `python manage.py migrate --fake-initial` or recreate test database. |
| **DB** | Slow query on document timeline | Missing composite index on `(patient_id, document_date)` | Verify `models.Index(fields=['patient', 'document_date'])` is migrated. |
| **Sharing** | `QR token expired` error immediately | UTC time mismatch between server and patient device | Always use `timezone.now()` instead of `datetime.now()` in Django models. |
| **Sharing** | Doctor can't see patient reports after scan | Handshake saved without active flag or wrong doctor UUID | Verify `ConsultationShare.is_active=True` and `expires_at > timezone.now()`. |
| **Meds** | Daily reminders not firing | Celery Beat is not running | Run `celery -A config beat -l INFO` in terminal or check `celery_beat` container. |
| **CORS** | `CORS policy: No 'Access-Control-Allow-Origin' header` | React frontend URL not in `CORS_ALLOWED_ORIGINS` | Add `http://localhost:3000` to `CORS_ALLOWED_ORIGINS` in `config/settings/base.py`. |
| **Upload** | `413 Request Entity Too Large` | Nginx or Django rejecting file `> 10MB` | Set `client_max_body_size 15M;` in Nginx and `DATA_UPLOAD_MAX_MEMORY_SIZE = 15728640`. |
| **PDF** | `WeasyPrint error: cannot load library 'gobject-2.0'` | Missing GTK3 libraries on Windows host | Install GTK3 runtime on Windows or run WeasyPrint inside Docker container. |
| **SMS** | Patient doesn't receive token SMS | Invalid Bangladeshi number format (missing `+880` prefix) | Standardize phone number using helper: `re.sub(r'[^0-9+]', '', phone)`. |
| **RAG** | Ask AI returns *"তথ্য পাওয়া যায়নি"* for existing doc | Chunking missed text or patient ID filter mismatch | Verify `metadata={'patient_id': str(doc.patient.id)}` matches user profile ID exactly. |
| **Prescription**| Drug interaction check returns 500 | One of the medication objects passed null name | Add input validation: filter out medications where `brand_name.strip() == ''`. |
| **Docker** | `port is already allocated: 0.0.0.0:6379` | Local native Redis service running on host | Run `net stop redis` on Windows or change host port mapping to `6380:6379`. |
| **Docker** | File upload fails with `PermissionDenied` in container | Docker volume mounted with root permissions | Ensure media directory in container has ownership `chown -R 1000:1000 /app/media`. |
| **React** | Charts not rendering in Health Logs tab | Recharts data array contains `null` or `string` values | Cast numerical fields to float: `parseFloat(item.glucose_value_mmol)`. |
| **React** | Camera modal opens black screen | Browser permissions denied or HTTPS required | In mobile browser, camera access requires `localhost` or valid `https://` origin. |
| **React** | QR code scanner cannot decode on mobile | Low contrast or camera focus too close | Use `html5-qrcode` library with `qrbox: { width: 250, height: 250 }`. |
| **Signal** | Infinite recursion on post_save signal | Signal handler calls `instance.save()` without `update_fields` | Always pass `update_fields=['is_danger']` or disconnect signal before save. |

