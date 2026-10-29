# MediVault — Setup Guide

> **MediVault** is an AI-Powered Personal Health Record and Patient–Doctor Communication Platform.
> This guide walks you through every step needed to get the full development environment running on your local machine — from installing prerequisites to verifying each service.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Google Cloud Vision Setup](#2-google-cloud-vision-setup)
3. [OpenAI API Setup](#3-openai-api-setup)
4. [SMTP Email Setup (Zero-Cost Dev Notifications)](#4-smtp-email-setup-zero-cost-dev-notifications)
5. [Environment Variables](#5-environment-variables)
6. [Docker Compose Setup (Recommended)](#6-docker-compose-setup-recommended)
7. [Manual Setup (Without Docker)](#7-manual-setup-without-docker)
8. [Database Initialization](#8-database-initialization)
9. [Verification Checklist](#9-verification-checklist)
10. [Common Issues & Troubleshooting](#10-common-issues--troubleshooting)
11. [IDE Setup](#11-ide-setup)

---

## 1. Prerequisites

Before you begin, make sure the following tools are installed on your system. The table lists the **minimum** version required and the command to verify you have it.

| Tool | Min Version | Verify Command | Download Link |
|------|-------------|----------------|---------------|
| **Python** | 3.12+ | `python --version` | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 20+ | `node --version` | [nodejs.org](https://nodejs.org/) |
| **npm** | 10+ | `npm --version` | Bundled with Node.js |
| **Yarn** *(optional)* | 1.22+ | `yarn --version` | `npm install -g yarn` |
| **Docker** | 24+ | `docker --version` | [docker.com](https://www.docker.com/products/docker-desktop/) |
| **Docker Compose** | 2.20+ | `docker compose version` | Bundled with Docker Desktop |
| **Git** | 2.40+ | `git --version` | [git-scm.com](https://git-scm.com/) |
| **PostgreSQL** | 16 | `psql --version` | [postgresql.org](https://www.postgresql.org/download/) *(or use Docker)* |
| **Redis** | 7+ | `redis-cli --version` | [redis.io](https://redis.io/download/) *(or use Docker)* |

> [!IMPORTANT]
> If you plan to use the **Docker Compose** setup (Section 5), you do **not** need to install PostgreSQL or Redis natively — they will run inside containers.

### Additional Accounts Required

| Service | Purpose | Sign-up Link |
|---------|---------|--------------|
| **Google Cloud** | Cloud Vision API for OCR | [console.cloud.google.com](https://console.cloud.google.com/) |
| **OpenAI** | GPT-4o-mini for AI features & embeddings | [platform.openai.com](https://platform.openai.com/) |

---

## 2. Google Cloud Vision Setup

MediVault uses the **Google Cloud Vision API** to perform OCR on uploaded prescriptions, lab reports, and medical documents. Follow these steps to configure it.

### Step 1 — Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the **project selector** dropdown at the top of the page.
3. Click **New Project**.
4. Enter the project name: `MediVault` (or any name you prefer).
5. Select your billing account (you may need to set one up — Google offers a free tier with $300 in credits).
6. Click **Create** and wait for the project to be provisioned.
7. Make sure your new project is **selected** in the project selector dropdown.

### Step 2 — Enable the Cloud Vision API

1. In the Cloud Console, navigate to **APIs & Services → Library**.
   - Direct link: [https://console.cloud.google.com/apis/library](https://console.cloud.google.com/apis/library)
2. Search for **Cloud Vision API**.
3. Click on **Cloud Vision API** in the results.
4. Click **Enable**.
5. Wait for the API to be enabled (a green checkmark will appear).

### Step 3 — Create a Service Account

1. Navigate to **IAM & Admin → Service Accounts**.
   - Direct link: [https://console.cloud.google.com/iam-admin/serviceaccounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Click **+ Create Service Account**.
3. Fill in the details:
   - **Service account name:** `medivault-vision`
   - **Service account ID:** `medivault-vision` (auto-generated)
   - **Description:** `Service account for MediVault OCR processing`
4. Click **Create and Continue**.
5. In the **Grant this service account access to project** step:
   - Search for and select the role: **Cloud Vision AI User** (`roles/cloudvision.user`).
   - If you don't find that exact role, use **Cloud Vision API User** or simply **Editor** for development.
6. Click **Continue**, then **Done**.

### Step 4 — Download JSON Credentials

1. In the Service Accounts list, find the `medivault-vision` account you just created.
2. Click the **three-dot menu (⋮)** on the right → **Manage keys**.
3. Click **Add Key → Create new key**.
4. Select **JSON** as the key type.
5. Click **Create**.
6. A `.json` file will be downloaded automatically. **Keep this file safe — it is your secret credential.**
7. Rename it to something descriptive:
   ```
   medivault-gcp-credentials.json
   ```
8. Move it to a secure location within your project (but **never** commit it to Git):
   ```bash
   # Example: place it in the project root (it's gitignored)
   mv ~/Downloads/medivault-gcp-credentials.json ./medivault-gcp-credentials.json
   ```

### Step 5 — Set the Environment Variable

Add the path to your credentials file as an environment variable:

**Linux / macOS:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/medivault-gcp-credentials.json"
```

**Windows (PowerShell):**
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\medivault-gcp-credentials.json"
```

**Windows (Command Prompt):**
```cmd
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\medivault-gcp-credentials.json
```

> [!TIP]
> For development, add `GOOGLE_APPLICATION_CREDENTIALS` to your `.env` file (see [Section 4](#4-environment-variables)) so it's automatically loaded. In Docker, mount the credentials file as a volume.

### Verification

Test that your credentials work with a quick API call:

```bash
# Install the Google Cloud CLI if you haven't already
# https://cloud.google.com/sdk/docs/install

gcloud auth activate-service-account --key-file=medivault-gcp-credentials.json
gcloud ml vision detect-text ./test-image.png
```

If you see extracted text from the image, your setup is working correctly.

---

## 3. OpenAI API Setup

MediVault uses **OpenAI GPT-4o-mini** for AI-powered features like document summarization, pre-appointment briefs, health report generation, and the "Ask AI" RAG system. It also uses **text-embedding-3-small** for document embeddings stored in ChromaDB.

### Step 1 — Create an OpenAI Account

1. Go to [https://platform.openai.com/signup](https://platform.openai.com/signup).
2. Sign up with your email or Google/Microsoft account.
3. Complete email verification and phone verification.

### Step 2 — Generate an API Key

1. Log in to [https://platform.openai.com/](https://platform.openai.com/).
2. Navigate to **API keys** in the left sidebar.
   - Direct link: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
3. Click **+ Create new secret key**.
4. Give it a name: `MediVault Development`.
5. Set permissions: **All** (for development).
6. Click **Create secret key**.
7. **Copy the key immediately** — you will not be able to see it again.
8. Store it securely (e.g., in a password manager or your `.env` file).

### Step 3 — Set Billing Limits

1. Navigate to **Settings → Billing** in the OpenAI dashboard.
   - Direct link: [https://platform.openai.com/settings/organization/billing](https://platform.openai.com/settings/organization/billing)
2. Add a payment method if you haven't already.
3. Go to **Settings → Limits**.
   - Direct link: [https://platform.openai.com/settings/organization/limits](https://platform.openai.com/settings/organization/limits)
4. Set a **monthly budget limit** to avoid unexpected charges:
   - Recommended for development: **$10 – $25 / month**.
5. Optionally set an **email notification threshold** (e.g., at $5).

> [!NOTE]
> **GPT-4o-mini** is very cost-effective (approximately $0.15 per 1M input tokens and $0.60 per 1M output tokens as of 2024). For development, you're unlikely to exceed a few dollars per month. The **text-embedding-3-small** model costs approximately $0.02 per 1M tokens.

### Step 4 — Set the Environment Variable

Add your API key to the environment:

**Linux / macOS:**
```bash
export OPENAI_API_KEY="sk-proj-..."
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY = "sk-proj-..."
```

### Verification

Test your API key with a quick curl command:

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 10
  }'
```

You should receive a JSON response with the AI's reply.

---

## 4. SMTP Email Setup (Zero-Cost Dev Notifications)

In Bangladesh, third-party SMS aggregator gateways (e.g. GP, Robi, Banglalink, SSL Wireless) incur recurring per-message costs. During active development, local testing, and user prototyping, MediVault routes all notification events (**Registration OTPs**, **Chamber Queue Token Calls**, **Danger Alert Broadcasts**, and **Follow-up Reminders**) through **SMTP Email**.

When you are ready to launch in production, you can switch to SMS with a single configuration flag (`MESSAGING_BACKEND=sms`) without changing any application code.

### Option A: Gmail SMTP with App Password (Fastest & Free)

If you have a Google / Gmail account, you can use Google's free SMTP server (`smtp.gmail.com`):

1. Go to your **Google Account**: [https://myaccount.google.com/](https://myaccount.google.com/)
2. Navigate to **Security** on the left menu.
3. Ensure **2-Step Verification** is turned **ON**.
4. In the search bar at the top, type **"App passwords"** (or go directly to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)).
5. Under **App name**, type `MediVault Dev` and click **Create**.
6. Google will display a 16-character password (e.g. `abcd efgh ijkl mnop`). **Copy this password** (spaces are ignored).
7. In your `.env` file, configure:
   ```dotenv
   MESSAGING_BACKEND=email
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-16-char-app-password
   DEFAULT_FROM_EMAIL=MediVault Health <your-email@gmail.com>
   ```

### Option B: SendGrid / Mailgun (Free Developer Tiers)

1. Create a free account at [SendGrid](https://sendgrid.com/) (100 free emails/day) or [Mailgun](https://www.mailgun.com/).
2. Create an API Key with "Mail Send" permissions.
3. Configure your `.env`:
   ```dotenv
   MESSAGING_BACKEND=email
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.sendgrid.net
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=apikey
   EMAIL_HOST_PASSWORD=<your-sendgrid-api-key>
   DEFAULT_FROM_EMAIL=MediVault Notifications <verified-sender@yourdomain.com>
   ```

### Option C: Console Backend (Zero-Setup Offline Testing)

If you are developing completely offline or do not wish to send actual emails:
```dotenv
MESSAGING_BACKEND=email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```
Django will print all OTP verification codes and token alerts directly to your terminal standard output!

---

## 5. Environment Variables

MediVault uses a `.env` file in the project root to manage configuration. Create this file by copying the example below.

### Create the `.env` File

```bash
# From the project root
cp .env.example .env
```

If `.env.example` doesn't exist yet, create `.env` manually with the contents below.

### Complete `.env.example`

Save the following as `.env.example` in the project root **and** copy it to `.env`, then fill in the values marked with `<REPLACE>`:

```dotenv
# ==============================================================================
# MediVault Environment Configuration
# ==============================================================================
# Copy this file to .env and replace placeholder values with your actual config.
# NEVER commit the .env file to version control.
# ==============================================================================

# ──────────────────────────────────────────────
# Django Core
# ──────────────────────────────────────────────
# Generate a secret key: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY=<REPLACE-with-a-long-random-string>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# ──────────────────────────────────────────────
# Database (PostgreSQL)
# ──────────────────────────────────────────────
DATABASE_URL=postgres://medivault_user:medivault_pass@localhost:5432/medivault
DB_NAME=medivault
DB_USER=medivault_user
DB_PASSWORD=<REPLACE-with-a-strong-password>
DB_HOST=localhost
DB_PORT=5432

# ──────────────────────────────────────────────
# Redis
# ──────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# ──────────────────────────────────────────────
# Google Cloud Vision (OCR)
# ──────────────────────────────────────────────
GOOGLE_APPLICATION_CREDENTIALS=/path/to/medivault-gcp-credentials.json
GCP_PROJECT_ID=<REPLACE-with-your-gcp-project-id>

# ──────────────────────────────────────────────
# OpenAI (AI Features)
# ──────────────────────────────────────────────
OPENAI_API_KEY=<REPLACE-with-your-openai-api-key>
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# ──────────────────────────────────────────────
# ChromaDB (Vector Database)
# ──────────────────────────────────────────────
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_COLLECTION=medivault_documents

# ──────────────────────────────────────────────
# JWT Authentication
# ──────────────────────────────────────────────
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=7

# ──────────────────────────────────────────────
# Messaging & Notifications (Email vs SMS Toggle)
# ──────────────────────────────────────────────
# Options: 'email' (development/prototype default) or 'sms' (production live)
MESSAGING_BACKEND=email

# SMTP Email Configuration (Used when MESSAGING_BACKEND=email)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<REPLACE-with-your-smtp-email>
EMAIL_HOST_PASSWORD=<REPLACE-with-your-smtp-app-password>
DEFAULT_FROM_EMAIL=MediVault Health <notifications@medivault.app>

# SMS Notifications (Activated when MESSAGING_BACKEND=sms)
SMS_API_KEY=<REPLACE-or-leave-empty-for-dev>
SMS_SENDER_ID=MediVault

# ──────────────────────────────────────────────
# File Storage
# ──────────────────────────────────────────────
MEDIA_ROOT=/app/media/
MAX_UPLOAD_SIZE=10485760

# ──────────────────────────────────────────────
# Frontend / CORS
# ──────────────────────────────────────────────
FRONTEND_URL=http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

### Variable Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | Django cryptographic signing key. Must be unique and secret. |
| `DEBUG` | ✅ | `True` for development, **always `False` in production**. |
| `ALLOWED_HOSTS` | ✅ | Comma-separated list of hostnames the server will accept. |
| `DATABASE_URL` | ✅ | Full PostgreSQL connection URI. |
| `DB_NAME` | ✅ | PostgreSQL database name. |
| `DB_USER` | ✅ | PostgreSQL user with access to the database. |
| `DB_PASSWORD` | ✅ | Password for the database user. |
| `DB_HOST` | ✅ | Database host. Use `localhost` for manual setup, `db` for Docker. |
| `DB_PORT` | ✅ | PostgreSQL port (default: `5432`). |
| `REDIS_URL` | ✅ | Redis connection URI for Django Channels (WebSocket). |
| `CELERY_BROKER_URL` | ✅ | Redis connection URI for Celery task broker (uses DB 1). |
| `GOOGLE_APPLICATION_CREDENTIALS` | ✅ | Absolute path to your GCP service account JSON key file. |
| `GCP_PROJECT_ID` | ✅ | Your Google Cloud project ID. |
| `OPENAI_API_KEY` | ✅ | Your OpenAI API secret key. |
| `OPENAI_MODEL` | ❌ | AI model for chat/completion (default: `gpt-4o-mini`). |
| `OPENAI_EMBEDDING_MODEL` | ❌ | Embedding model for vector search (default: `text-embedding-3-small`). |
| `CHROMA_HOST` | ✅ | ChromaDB server host. Use `localhost` for manual, `chromadb` for Docker. |
| `CHROMA_PORT` | ✅ | ChromaDB server port (default: `8000`). |
| `CHROMA_COLLECTION` | ❌ | ChromaDB collection name (default: `medivault_documents`). |
| `JWT_ACCESS_TOKEN_LIFETIME` | ❌ | Access token lifetime in minutes (default: `60`). |
| `JWT_REFRESH_TOKEN_LIFETIME` | ❌ | Refresh token lifetime in days (default: `7`). |
| `MESSAGING_BACKEND` | ✅ | Dispatcher backend: `'email'` (dev/prototype default) or `'sms'` (production). |
| `EMAIL_BACKEND` | ❌ | Django email backend class (default: `django.core.mail.backends.smtp.EmailBackend`). |
| `EMAIL_HOST` | ⚠️ | SMTP server host (e.g. `smtp.gmail.com`, `smtp.sendgrid.net`). |
| `EMAIL_PORT` | ❌ | SMTP port (default: `587`). |
| `EMAIL_USE_TLS` | ❌ | Use TLS encryption for SMTP (default: `True`). |
| `EMAIL_HOST_USER` | ⚠️ | SMTP user account / email address. |
| `EMAIL_HOST_PASSWORD` | ⚠️ | SMTP password or App Password. |
| `DEFAULT_FROM_EMAIL` | ❌ | Default sender address appearing in the From header. |
| `SMS_API_KEY` | ❌ | SMS provider API key (needed only when `MESSAGING_BACKEND=sms`). |
| `SMS_SENDER_ID` | ❌ | SMS sender name (default: `MediVault`). |
| `MEDIA_ROOT` | ❌ | Directory for uploaded files (default: `/app/media/`). |
| `MAX_UPLOAD_SIZE` | ❌ | Max upload size in bytes (default: `10485760` = 10 MB). |
| `FRONTEND_URL` | ✅ | URL where the React frontend is running. |
| `CORS_ALLOWED_ORIGINS` | ✅ | Comma-separated origins allowed for CORS. |

> [!CAUTION]
> **Never commit your `.env` file to Git.** Make sure `.env` is listed in your `.gitignore`. The `.env.example` file (with placeholder values) *should* be committed so other developers know what variables are needed.

### Generating a Django Secret Key

Run this one-liner to generate a secure secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and paste it as the `SECRET_KEY` value in your `.env` file.

---

## 5. Docker Compose Setup (Recommended)

Docker Compose is the **recommended** way to run MediVault in development. It sets up all services — Django, PostgreSQL, Redis, Celery, ChromaDB, and the React frontend — in isolated containers with a single command.

### 5.1 — Project File Structure (Expected)

Before running Docker Compose, ensure your project has this general structure:

```
MediVault/
├── backend/                  # Django project
│   ├── manage.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── medivault/            # Django settings package
│       ├── __init__.py
│       ├── settings.py
│       ├── urls.py
│       ├── wsgi.py
│       ├── asgi.py
│       └── celery.py
├── frontend/                 # React application
│   ├── package.json
│   ├── Dockerfile
│   └── src/
├── docker-compose.yml
├── .env
├── .env.example
├── .gitignore
└── docs/
```

### 5.2 — Backend Dockerfile

Create `backend/Dockerfile`:

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (needed for psycopg2, Pillow, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

# Expose port
EXPOSE 8000

# Default command (overridden by docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### 5.3 — Frontend Dockerfile

Create `frontend/Dockerfile`:

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* yarn.lock* ./
RUN npm install

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Start dev server
CMD ["npm", "start"]
```

### 5.4 — docker-compose.yml

Save the following as `docker-compose.yml` in the project root:

```yaml
# ==============================================================================
# MediVault — Docker Compose (Development)
# ==============================================================================
# Usage:
#   docker compose up -d          # Start all services
#   docker compose down            # Stop all services
#   docker compose logs -f web     # Follow Django logs
#   docker compose exec web bash   # Shell into the Django container
# ==============================================================================

services:
  # ── PostgreSQL 16 ──────────────────────────────────────────────────────────
  db:
    image: postgres:16-alpine
    container_name: medivault-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DB_NAME:-medivault}
      POSTGRES_USER: ${DB_USER:-medivault_user}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-medivault_pass}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-medivault_user} -d ${DB_NAME:-medivault}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - medivault-network

  # ── Redis 7 ────────────────────────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    container_name: medivault-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - medivault-network

  # ── ChromaDB ───────────────────────────────────────────────────────────────
  chromadb:
    image: chromadb/chroma:latest
    container_name: medivault-chromadb
    restart: unless-stopped
    ports:
      - "8100:8000"
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE
    networks:
      - medivault-network

  # ── Django Backend (Web) ───────────────────────────────────────────────────
  web:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: medivault-web
    restart: unless-stopped
    command: >
      sh -c "
        python manage.py migrate --noinput &&
        python manage.py runserver 0.0.0.0:8000
      "
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - media_data:/app/media
      - ./medivault-gcp-credentials.json:/app/credentials/gcp-credentials.json:ro
    env_file:
      - .env
    environment:
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/gcp-credentials.json
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      chromadb:
        condition: service_started
    networks:
      - medivault-network

  # ── Celery Worker ──────────────────────────────────────────────────────────
  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: medivault-celery-worker
    restart: unless-stopped
    command: celery -A medivault worker -l info --concurrency=2
    volumes:
      - ./backend:/app
      - media_data:/app/media
      - ./medivault-gcp-credentials.json:/app/credentials/gcp-credentials.json:ro
    env_file:
      - .env
    environment:
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/gcp-credentials.json
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - medivault-network

  # ── Celery Beat (Periodic Task Scheduler) ──────────────────────────────────
  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: medivault-celery-beat
    restart: unless-stopped
    command: celery -A medivault beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - ./backend:/app
    env_file:
      - .env
    environment:
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - medivault-network

  # ── React Frontend (Dev Server) ────────────────────────────────────────────
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: medivault-frontend
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - REACT_APP_API_URL=http://localhost:8000/api
      - REACT_APP_WS_URL=ws://localhost:8000/ws
      - WATCHPACK_POLLING=true
    depends_on:
      - web
    networks:
      - medivault-network

# ── Volumes ────────────────────────────────────────────────────────────────────
volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  chroma_data:
    driver: local
  media_data:
    driver: local

# ── Networks ───────────────────────────────────────────────────────────────────
networks:
  medivault-network:
    driver: bridge
```

### 5.5 — Running with Docker Compose

#### First-Time Setup

```bash
# 1. Clone the repository (if you haven't already)
git clone <repository-url> MediVault
cd MediVault

# 2. Create your .env file
cp .env.example .env
# Edit .env and fill in your actual values (see Section 4)

# 3. Place your GCP credentials file in the project root
cp /path/to/your/medivault-gcp-credentials.json ./medivault-gcp-credentials.json

# 4. Build and start all services
docker compose up -d --build

# 5. Watch the logs to see everything starting up
docker compose logs -f
```

#### Everyday Commands

```bash
# Start all services (detached)
docker compose up -d

# Stop all services
docker compose down

# Restart a specific service
docker compose restart web

# View logs for a specific service
docker compose logs -f web
docker compose logs -f celery-worker

# Open a shell inside the Django container
docker compose exec web bash

# Run Django management commands inside the container
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py shell

# Rebuild after changing Dockerfile or requirements.txt
docker compose up -d --build web

# Remove all containers, volumes, and networks (DESTRUCTIVE — deletes DB data)
docker compose down -v
```

> [!WARNING]
> `docker compose down -v` will **delete all data** in your PostgreSQL, Redis, and ChromaDB volumes. Only use it when you want a completely fresh start.

### 5.6 — Service Port Reference (Docker)

| Service | Container Name | Internal Port | Host Port | URL |
|---------|---------------|---------------|-----------|-----|
| Django API | `medivault-web` | 8000 | **8000** | [http://localhost:8000](http://localhost:8000) |
| React Frontend | `medivault-frontend` | 3000 | **3000** | [http://localhost:3000](http://localhost:3000) |
| PostgreSQL | `medivault-db` | 5432 | **5432** | `psql -h localhost -p 5432 -U medivault_user -d medivault` |
| Redis | `medivault-redis` | 6379 | **6379** | `redis-cli -h localhost -p 6379` |
| ChromaDB | `medivault-chromadb` | 8000 | **8100** | [http://localhost:8100](http://localhost:8100) |

> [!NOTE]
> ChromaDB is mapped to host port **8100** (not 8000) to avoid conflicts with the Django server. When connecting from within Docker, services use the internal hostname `chromadb` on port `8000`. When connecting from the host machine, use `localhost:8100`.

---

## 6. Manual Setup (Without Docker)

If you prefer to run services directly on your machine (without Docker), follow the steps below for each component.

### 6.1 — Backend Setup (Django)

```bash
# ── 1. Navigate to the project root ──
cd MediVault

# ── 2. Create a Python virtual environment ──
python -m venv venv

# ── 3. Activate the virtual environment ──
# Linux / macOS:
source venv/bin/activate
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (Command Prompt):
venv\Scripts\activate.bat

# ── 4. Upgrade pip ──
pip install --upgrade pip

# ── 5. Install Python dependencies ──
pip install -r backend/requirements.txt

# ── 6. Create the .env file (if not already done) ──
cp .env.example .env
# Edit .env with your actual values — see Section 4

# ── 7. Configure the database ──
# Make sure PostgreSQL is running and create the database:
# Linux / macOS:
sudo -u postgres psql -c "CREATE USER medivault_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "CREATE DATABASE medivault OWNER medivault_user;"
sudo -u postgres psql -c "ALTER USER medivault_user CREATEDB;"
# Windows (in psql shell):
# CREATE USER medivault_user WITH PASSWORD 'your_password';
# CREATE DATABASE medivault OWNER medivault_user;
# ALTER USER medivault_user CREATEDB;

# ── 8. Run database migrations ──
cd backend
python manage.py makemigrations
python manage.py migrate

# ── 9. Create a superuser (admin account) ──
python manage.py createsuperuser
# Follow the prompts to set username, email, and password

# ── 10. Start the development server ──
python manage.py runserver
# Server will be available at http://localhost:8000
```

> [!TIP]
> For WebSocket support (real-time queue updates), run the server with Daphne (ASGI) instead of the default WSGI server:
> ```bash
> daphne -b 0.0.0.0 -p 8000 medivault.asgi:application
> ```

### 6.2 — Frontend Setup (React)

Open a **new terminal window** (keep the backend server running):

```bash
# ── 1. Navigate to the frontend directory ──
cd MediVault/frontend

# ── 2. Install Node.js dependencies ──
npm install
# Or with Yarn:
# yarn install

# ── 3. Create frontend environment file ──
# Create a .env file inside the frontend/ directory:
cat > .env << 'EOF'
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_WS_URL=ws://localhost:8000/ws
EOF

# Windows (PowerShell):
# @"
# REACT_APP_API_URL=http://localhost:8000/api
# REACT_APP_WS_URL=ws://localhost:8000/ws
# "@ | Out-File -FilePath .env -Encoding utf8

# ── 4. Start the development server ──
npm start
# Or with Yarn:
# yarn start

# React dev server will be available at http://localhost:3000
```

### 6.3 — Redis Setup (Manual)

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify Redis is running
redis-cli ping
# Expected output: PONG
```

**macOS (Homebrew):**
```bash
brew install redis
brew services start redis

# Verify
redis-cli ping
```

**Windows:**
Redis does not natively support Windows. Use one of the following options:

```powershell
# Option 1: Use Docker for just Redis
docker run -d --name medivault-redis -p 6379:6379 redis:7-alpine

# Option 2: Use WSL2
# Install Redis inside WSL2 Ubuntu and run it there

# Option 3: Use Memurai (Redis-compatible for Windows)
# Download from https://www.memurai.com/
```

### 6.4 — ChromaDB Setup (Manual)

```bash
# ── Option A: Run with Docker (recommended even in manual setup) ──
docker run -d \
  --name medivault-chromadb \
  -p 8100:8000 \
  -v chroma_data:/chroma/chroma \
  -e IS_PERSISTENT=TRUE \
  -e ANONYMIZED_TELEMETRY=FALSE \
  chromadb/chroma:latest

# ── Option B: Run with Python ──
pip install chromadb

# Start the ChromaDB server
chroma run --host localhost --port 8100 --path ./chroma_data
```

### 6.5 — Celery Setup

Open **two more terminal windows** (keep the backend and frontend running):

**Terminal 3 — Celery Worker:**
```bash
# Navigate to the backend directory and activate the virtualenv
cd MediVault/backend
source ../venv/bin/activate  # Linux/macOS
# .\venv\Scripts\Activate.ps1  # Windows PowerShell

# Start the Celery worker
celery -A medivault worker -l info --concurrency=2

# Expected output:
# [INFO] Connected to redis://localhost:6379/1
# [INFO] celery@hostname ready.
```

**Terminal 4 — Celery Beat (periodic task scheduler):**
```bash
cd MediVault/backend
source ../venv/bin/activate  # Linux/macOS
# .\venv\Scripts\Activate.ps1  # Windows PowerShell

# Start the Celery Beat scheduler
celery -A medivault beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Expected output:
# [INFO] beat: Starting...
```

> [!NOTE]
> Celery Beat uses `django_celery_beat.schedulers:DatabaseScheduler` so that periodic tasks (like monthly health report generation) can be managed through the Django admin interface.

### 6.6 — Summary of Running Processes (Manual)

When running manually, you'll need **5 terminal windows** active:

| Terminal | Process | Command | Port |
|----------|---------|---------|------|
| 1 | Django Backend | `python manage.py runserver` | 8000 |
| 2 | React Frontend | `npm start` | 3000 |
| 3 | Celery Worker | `celery -A medivault worker -l info` | — |
| 4 | Celery Beat | `celery -A medivault beat -l info` | — |
| 5 | ChromaDB | `docker run ... chromadb/chroma` | 8100 |

Plus background services: **PostgreSQL** (port 5432) and **Redis** (port 6379).

---

## 7. Database Initialization

### 7.1 — Running Migrations

Migrations create and update the database schema. Run them every time you pull new code or after creating new models.

```bash
# If using Docker:
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# If running manually:
cd backend
python manage.py makemigrations
python manage.py migrate
```

**Expected output (first time):**

```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, ...
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  ...
```

### 7.2 — Creating the Initial Superuser

The superuser has full access to the Django admin panel at `/admin/`.

```bash
# Docker:
docker compose exec web python manage.py createsuperuser

# Manual:
python manage.py createsuperuser
```

Follow the prompts:

```
Username: admin
Email address: admin@medivault.local
Password: ********
Password (again): ********
Superuser created successfully.
```

### 7.3 — Seed Data Script

Create a management command to seed sample data for development. Save this as `backend/core/management/commands/seed_data.py` (adjust the app name `core` to match your actual Django app):

```python
"""
MediVault — Seed Data Command
Usage:
    python manage.py seed_data
    docker compose exec web python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds the database with sample development data"

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seeding MediVault database...")

        # ── 1. Create sample Doctor ──
        doctor, created = User.objects.get_or_create(
            username="dr.rahman",
            defaults={
                "email": "dr.rahman@medivault.local",
                "first_name": "Dr. Anika",
                "last_name": "Rahman",
                "is_staff": False,
                # Set the role field according to your User model
                # "role": "doctor",
            },
        )
        if created:
            doctor.set_password("doctor123")
            doctor.save()
            self.stdout.write(self.style.SUCCESS("  ✅ Created doctor: dr.rahman / doctor123"))
        else:
            self.stdout.write("  ⏭️  Doctor dr.rahman already exists")

        # ── 2. Create sample Patient ──
        patient, created = User.objects.get_or_create(
            username="patient.karim",
            defaults={
                "email": "karim@medivault.local",
                "first_name": "Karim",
                "last_name": "Hossain",
                "is_staff": False,
                # "role": "patient",
            },
        )
        if created:
            patient.set_password("patient123")
            patient.save()
            self.stdout.write(self.style.SUCCESS("  ✅ Created patient: patient.karim / patient123"))
        else:
            self.stdout.write("  ⏭️  Patient patient.karim already exists")

        # ── 3. Create sample Clinic Assistant ──
        assistant, created = User.objects.get_or_create(
            username="assistant.fatima",
            defaults={
                "email": "fatima@medivault.local",
                "first_name": "Fatima",
                "last_name": "Begum",
                "is_staff": False,
                # "role": "assistant",
            },
        )
        if created:
            assistant.set_password("assistant123")
            assistant.save()
            self.stdout.write(
                self.style.SUCCESS("  ✅ Created assistant: assistant.fatima / assistant123")
            )
        else:
            self.stdout.write("  ⏭️  Assistant assistant.fatima already exists")

        # ── 4. Create sample Clinic (if you have a Clinic model) ──
        # from clinics.models import Clinic
        # clinic, created = Clinic.objects.get_or_create(
        #     name="MediVault Demo Clinic",
        #     defaults={
        #         "address": "123 Health Street, Dhaka",
        #         "phone": "+880-1700-000000",
        #         "doctor": doctor,
        #     },
        # )
        # if created:
        #     clinic.assistants.add(assistant)
        #     self.stdout.write(self.style.SUCCESS("  ✅ Created clinic: MediVault Demo Clinic"))

        self.stdout.write(self.style.SUCCESS("\n🎉 Seed data created successfully!"))
        self.stdout.write("\nSample Credentials:")
        self.stdout.write("  Doctor:    dr.rahman / doctor123")
        self.stdout.write("  Patient:   patient.karim / patient123")
        self.stdout.write("  Assistant: assistant.fatima / assistant123")
```

Run the seed command:

```bash
# Docker:
docker compose exec web python manage.py seed_data

# Manual:
python manage.py seed_data
```

> [!NOTE]
> Adjust the seed script to match your actual User model fields. If you use a custom `role` field, a `Profile` model, or a `Clinic` model, uncomment and modify the relevant sections.

---

## 8. Verification Checklist

After completing setup, walk through this checklist to verify that every component is running correctly.

### Run All Checks

```bash
# Quick status check for Docker setup
docker compose ps
```

All services should show `Up` or `Up (healthy)`.

### Component-by-Component Verification

- [ ] **Django server running at `localhost:8000`**
  ```bash
  curl http://localhost:8000/admin/
  # Should return HTML (Django admin login page)
  ```

- [ ] **Swagger / API docs accessible at `localhost:8000/api/docs/`**
  ```bash
  curl -s http://localhost:8000/api/docs/ | head -20
  # Should return HTML (Swagger UI)
  ```
  Open in browser: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)

- [ ] **React app running at `localhost:3000`**
  ```bash
  curl -s http://localhost:3000 | head -5
  # Should return HTML
  ```
  Open in browser: [http://localhost:3000](http://localhost:3000)

- [ ] **PostgreSQL connection verified**
  ```bash
  # Docker:
  docker compose exec db psql -U medivault_user -d medivault -c "SELECT 1;"
  # Manual:
  psql -h localhost -U medivault_user -d medivault -c "SELECT 1;"
  # Expected: 1
  ```

- [ ] **Redis connection verified**
  ```bash
  # Docker:
  docker compose exec redis redis-cli ping
  # Manual:
  redis-cli ping
  # Expected: PONG
  ```

- [ ] **Celery worker processing tasks**
  ```bash
  # Docker:
  docker compose logs celery-worker | tail -5
  # Manual: check the Celery worker terminal
  # Should show: "celery@hostname ready."
  ```

- [ ] **Google Cloud Vision API responding**
  ```bash
  # Docker:
  docker compose exec web python -c "
  from google.cloud import vision
  client = vision.ImageAnnotatorClient()
  print('✅ Google Cloud Vision client initialized successfully')
  "
  # Manual (with venv activated):
  python -c "
  from google.cloud import vision
  client = vision.ImageAnnotatorClient()
  print('✅ Google Cloud Vision client initialized successfully')
  "
  ```

- [ ] **OpenAI API responding**
  ```bash
  # Docker:
  docker compose exec web python -c "
  import os
  from openai import OpenAI
  client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
  response = client.chat.completions.create(
      model='gpt-4o-mini',
      messages=[{'role': 'user', 'content': 'Say OK'}],
      max_tokens=5
  )
  print(f'✅ OpenAI API working: {response.choices[0].message.content}')
  "
  ```

- [ ] **ChromaDB running and accessible**
  ```bash
  # From host machine (port 8100):
  curl http://localhost:8100/api/v1/heartbeat
  # Expected: {"nanosecond heartbeat": ...}

  # From inside Docker (port 8000):
  docker compose exec web curl http://chromadb:8000/api/v1/heartbeat
  ```

- [ ] **WebSocket connection working**
  ```bash
  # Install wscat for testing WebSockets
  npm install -g wscat

  # Test the WebSocket connection (adjust the path to match your routing)
  wscat -c ws://localhost:8000/ws/queue/
  # Should connect successfully (or return an auth error, which still confirms WS is working)
  ```

---

## 9. Common Issues & Troubleshooting

### Database Connection Errors

**Symptom:** `django.db.utils.OperationalError: could not connect to server`

```bash
# Check if PostgreSQL is running
# Docker:
docker compose ps db
docker compose logs db

# Manual:
sudo systemctl status postgresql   # Linux
brew services list                  # macOS
```

**Common fixes:**
- Ensure `DB_HOST` is set to `db` (Docker) or `localhost` (manual).
- Ensure `DB_PASSWORD` in `.env` matches the password you set during database creation.
- Verify the database exists: `psql -U medivault_user -d medivault -c "SELECT 1;"`
- Check PostgreSQL is accepting connections on the expected port: `pg_isready -h localhost -p 5432`.

---

### Redis Connection Issues

**Symptom:** `redis.exceptions.ConnectionError: Error connecting to localhost:6379`

```bash
# Check if Redis is running
# Docker:
docker compose ps redis

# Manual:
redis-cli ping
```

**Common fixes:**
- Ensure Redis is installed and running.
- On Windows, Redis must run via Docker, WSL2, or Memurai (no native support).
- Check that `REDIS_URL` in `.env` matches the actual Redis address.
- For Docker, ensure the service name `redis` is used (not `localhost`) inside containers.

---

### Google Cloud Credentials Not Found

**Symptom:** `google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials`

**Common fixes:**
1. Verify the credentials file exists at the path specified in `GOOGLE_APPLICATION_CREDENTIALS`.
2. Ensure the path is **absolute**, not relative.
3. In Docker, confirm the volume mount is correct:
   ```yaml
   volumes:
     - ./medivault-gcp-credentials.json:/app/credentials/gcp-credentials.json:ro
   ```
4. Check file permissions — the file must be readable by the process.
5. Test manually:
   ```bash
   python -c "import google.auth; creds, proj = google.auth.default(); print(f'Project: {proj}')"
   ```

---

### OpenAI Rate Limits

**Symptom:** `openai.RateLimitError: Rate limit reached` or `429 Too Many Requests`

**Common fixes:**
- Check your [usage dashboard](https://platform.openai.com/usage) for current usage.
- Ensure you have billing set up (free-tier keys have very low limits).
- Add retry logic with exponential backoff in your code.
- Reduce `concurrency` on the Celery worker if many documents are being processed simultaneously.
- Consider caching AI responses for repeated queries.

---

### CORS Errors

**Symptom:** Browser console shows `Access to XMLHttpRequest at 'http://localhost:8000/api/...' from origin 'http://localhost:3000' has been blocked by CORS policy`

**Common fixes:**
1. Ensure `CORS_ALLOWED_ORIGINS` in `.env` includes `http://localhost:3000`.
2. Verify `django-cors-headers` is installed and in `INSTALLED_APPS`:
   ```python
   # settings.py
   INSTALLED_APPS = [
       ...
       'corsheaders',
       ...
   ]

   MIDDLEWARE = [
       'corsheaders.middleware.CorsMiddleware',  # Must be near the top
       'django.middleware.common.CommonMiddleware',
       ...
   ]
   ```
3. Check that the middleware is **above** `CommonMiddleware` in the list.
4. For development, you can temporarily use:
   ```python
   CORS_ALLOW_ALL_ORIGINS = True  # Only for development!
   ```

---

### Migration Conflicts

**Symptom:** `django.db.migrations.exceptions.InconsistentMigrationHistory` or merge conflicts in migration files

**Common fixes:**
```bash
# Show current migration status
python manage.py showmigrations

# If migrations are out of sync, try:
python manage.py migrate --run-syncdb

# If you have conflicting migration files, merge them:
python manage.py makemigrations --merge

# Nuclear option (development only — DESTROYS DATA):
# 1. Delete all migration files (except __init__.py) from each app
# 2. Drop and recreate the database
# 3. Run makemigrations and migrate fresh
```

---

### Docker Networking Issues

**Symptom:** Containers can't communicate with each other (e.g., Django can't reach PostgreSQL)

**Common fixes:**
1. Ensure all services are on the same Docker network (`medivault-network`).
2. Use **service names** (not `localhost`) for inter-container communication:
   - PostgreSQL: `db:5432`
   - Redis: `redis:6379`
   - ChromaDB: `chromadb:8000`
3. Inspect the network:
   ```bash
   docker network inspect medivault_medivault-network
   ```
4. Check container DNS resolution:
   ```bash
   docker compose exec web ping db
   docker compose exec web ping redis
   ```
5. Restart all services:
   ```bash
   docker compose down && docker compose up -d
   ```

---

### Port Already in Use

**Symptom:** `Error: listen EADDRINUSE: address already in use :::8000`

```bash
# Find what's using the port
# Linux/macOS:
lsof -i :8000
# Windows:
netstat -ano | findstr :8000

# Kill the process
# Linux/macOS:
kill -9 <PID>
# Windows:
taskkill /PID <PID> /F
```

---

## 10. IDE Setup

### 10.1 — VS Code Recommended Extensions

Install the following extensions for the best development experience. You can install them from the command line:

```bash
code --install-extension ms-python.python
code --install-extension ms-python.debugpy
code --install-extension ms-python.pylint
code --install-extension ms-python.black-formatter
code --install-extension dbaeumer.vscode-eslint
code --install-extension esbenp.prettier-vscode
code --install-extension ms-azuretools.vscode-docker
code --install-extension batisteo.vscode-django
code --install-extension dsznajder.es7-react-js-snippets
code --install-extension bradlc.vscode-tailwindcss
code --install-extension ms-vscode.vscode-typescript-next
code --install-extension eamodio.vscode-gitlens
code --install-extension usernamehw.errorlens
code --install-extension GitHub.copilot
```

**Extension summary:**

| Extension | Purpose |
|-----------|---------|
| Python | Python language support, IntelliSense |
| Debugpy | Python debugging |
| Pylint | Python linting |
| Black Formatter | Python code formatting |
| ESLint | JavaScript/TypeScript linting |
| Prettier | JavaScript/TypeScript/CSS formatting |
| Docker | Dockerfile and docker-compose support |
| Django | Django template syntax highlighting |
| ES7 React Snippets | React component boilerplate shortcuts |
| Tailwind CSS IntelliSense | Tailwind class autocomplete (if using Tailwind) |
| TypeScript Next | Latest TypeScript support |
| GitLens | Enhanced Git annotations |
| Error Lens | Inline error highlighting |
| GitHub Copilot | AI code completion (optional) |

### 10.2 — VS Code Settings

Create or update `.vscode/settings.json` in the project root:

```jsonc
{
  // ── Python ──
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.autoImportCompletions": true,

  // ── JavaScript / TypeScript / React ──
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "[javascriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },

  // ── Django ──
  "files.associations": {
    "**/*.html": "html",
    "**/templates/**/*.html": "django-html"
  },
  "emmet.includeLanguages": {
    "django-html": "html"
  },

  // ── General ──
  "editor.tabSize": 4,
  "editor.rulers": [88, 120],
  "files.trimTrailingWhitespace": true,
  "files.insertFinalNewline": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/node_modules": true,
    "**/.git": true
  }
}
```

### 10.3 — Python / Django Debugging Configuration

Create `.vscode/launch.json`:

```jsonc
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Django: Runserver",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/backend/manage.py",
      "args": ["runserver", "0.0.0.0:8000", "--noreload"],
      "django": true,
      "justMyCode": false,
      "envFile": "${workspaceFolder}/.env",
      "cwd": "${workspaceFolder}/backend"
    },
    {
      "name": "Django: Shell",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/backend/manage.py",
      "args": ["shell"],
      "django": true,
      "envFile": "${workspaceFolder}/.env",
      "cwd": "${workspaceFolder}/backend"
    },
    {
      "name": "Django: Migrate",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/backend/manage.py",
      "args": ["migrate"],
      "django": true,
      "envFile": "${workspaceFolder}/.env",
      "cwd": "${workspaceFolder}/backend"
    },
    {
      "name": "Celery: Worker",
      "type": "debugpy",
      "request": "launch",
      "module": "celery",
      "args": ["-A", "medivault", "worker", "-l", "info", "--concurrency=1"],
      "envFile": "${workspaceFolder}/.env",
      "cwd": "${workspaceFolder}/backend"
    },
    {
      "name": "Python: Current File",
      "type": "debugpy",
      "request": "launch",
      "program": "${file}",
      "envFile": "${workspaceFolder}/.env"
    },
    {
      "name": "React: Chrome",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:3000",
      "webRoot": "${workspaceFolder}/frontend/src",
      "sourceMaps": true
    }
  ],
  "compounds": [
    {
      "name": "Full Stack: Django + React",
      "configurations": ["Django: Runserver", "React: Chrome"]
    }
  ]
}
```

### 10.4 — ESLint Configuration

Create `frontend/.eslintrc.json`:

```json
{
  "env": {
    "browser": true,
    "es2021": true,
    "node": true,
    "jest": true
  },
  "extends": [
    "eslint:recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "plugin:jsx-a11y/recommended",
    "prettier"
  ],
  "parserOptions": {
    "ecmaFeatures": {
      "jsx": true
    },
    "ecmaVersion": "latest",
    "sourceType": "module"
  },
  "plugins": ["react", "react-hooks", "jsx-a11y"],
  "rules": {
    "react/react-in-jsx-scope": "off",
    "react/prop-types": "warn",
    "no-unused-vars": "warn",
    "no-console": "warn"
  },
  "settings": {
    "react": {
      "version": "detect"
    }
  }
}
```

### 10.5 — Prettier Configuration

Create `frontend/.prettierrc`:

```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "bracketSpacing": true,
  "jsxSingleQuote": false,
  "arrowParens": "always",
  "endOfLine": "lf"
}
```

Create `frontend/.prettierignore`:

```
node_modules
build
coverage
*.min.js
```

---

## Quick Start Summary

```mermaid
flowchart LR
    A["1. Clone Repo"] --> B["2. Set Up APIs"]
    B --> C["3. Create .env"]
    C --> D{"Docker?"}
    D -->|Yes| E["docker compose up -d"]
    D -->|No| F["Manual Setup"]
    F --> G["Backend + Frontend + Celery"]
    E --> H["4. Run Migrations"]
    G --> H
    H --> I["5. Create Superuser"]
    I --> J["6. Seed Data"]
    J --> K["7. Verify Checklist ✅"]
```

**Fastest path (Docker):**
```bash
git clone <repo-url> MediVault && cd MediVault
cp .env.example .env         # Edit with your API keys
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_data
# Open http://localhost:3000 🎉
```

---

*Last updated: October 2026*
