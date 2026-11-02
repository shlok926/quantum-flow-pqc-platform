# Developer Setup & Local Environment Guide

## 1. Document Purpose & Engineering Baseline

This document provides a comprehensive onboarding guide for software engineers, DevSecOps practitioners, and security analysts working on the **Quantum Flow Technologies PQC Discovery & Risk Assessment Platform**.

> [!IMPORTANT]
> **Implementation Baseline Status (Sprint 0 / Pre-Implementation):**  
> The repository is currently in its **repository organization, engineering setup, and architecture review stage**. The application source code (`apps/api/`, `apps/worker/`, `apps/web/`, `packages/scanner/`) has **not yet been created**.  
> In the instructions below, commands are explicitly labeled as:
> - `[ACTIVE / WORKING NOW]`: Commands that can be executed immediately against the current repository state (e.g., Git operations, directory checks, Python environment creation).
> - `[TARGET ARCHITECTURE / PLANNED FOR SPRINT 0-1]`: Commands that represent the approved standard workflow once application skeletons, dependency manifests (`pyproject.toml`, `package.json`), and container manifests (`docker-compose.yml`) are committed during Sprint 0.

---

## 2. System Prerequisites

Before starting local development, ensure your workstation meets the following requirements:

| Tool | Minimum Version | Recommended Version | Purpose |
|---|---|---|---|
| **Git** | 2.40+ | 2.45+ | Version control |
| **Python** | 3.12.0+ | 3.12.4+ | Backend services, scanner, risk engine |
| **Node.js** | 20.12.0 LTS | 20.x or 22.x LTS | Frontend application and web tooling |
| **Package Manager (JS)** | npm 10+ or pnpm 9+ | pnpm 9.x | Monorepo and frontend dependencies |
| **Docker** | 25.0+ | Latest Docker Desktop / Engine | Local PostgreSQL, Redis, container tests |
| **Docker Compose** | v2.24+ | Latest Compose v2 | Multi-container local orchestration |
| **PostgreSQL Client** | 15+ | `psql` 16 | Direct database debugging |

---

## 3. Repository Clone & Initial Inspection

### 3.1 Clone the Repository `[ACTIVE / WORKING NOW]`

```powershell
# Clone the repository
git clone https://github.com/shlok926/quantum-flow-pqc-platform.git
cd quantum-flow-pqc-platform

# Check git status and current branch
git status
```

### 3.2 Repository Directory Layout `[TARGET ARCHITECTURE]`

The planned monorepo layout (to be incrementally instantiated in Sprint 0) is:

```text
quantum-flow-pqc-platform/
├── apps/
│   ├── api/                 # FastAPI REST application (Control Plane)
│   ├── worker/              # Celery task worker (Execution Plane)
│   └── web/                 # React / Vite / TypeScript dashboard
├── packages/
│   ├── scanner/             # TLS collector, DNS safety, socket policy
│   ├── cbom/                # CBOM correlation & schema export engine
│   └── risk-engine/         # Deterministic quantum risk scoring engine
├── infra/
│   ├── docker/              # Dockerfiles and compose definitions
│   └── scripts/             # Local setup and database seed scripts
├── docs/                    # Technical specifications and guides
├── .env.example             # Safe environment variable template
├── .editorconfig            # Cross-IDE formatting standards
├── .gitignore               # Multi-ecosystem git ignore rules
├── CONTRIBUTING.md          # Contributor workflow summary
├── README.md                # Project documentation overview
└── SECURITY.md              # Vulnerability reporting policy
```

---

## 4. Backend Environment Setup

### 4.1 Python Virtual Environment `[ACTIVE / WORKING NOW]`

Create and activate an isolated Python 3.12 virtual environment:

#### Windows (PowerShell):
```powershell
# Verify Python version
python --version  # Must report Python 3.12.x

# Create virtual environment in .venv
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

*Note on Windows Execution Policy:* If PowerShell displays a script execution error, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

#### macOS / Linux (Bash):
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 4.2 Backend Dependency Installation `[TARGET ARCHITECTURE / SPRINT 0]`

Once `pyproject.toml` or `requirements.txt` is introduced in Sprint 0, install dependencies:

```powershell
# Planned command for Sprint 0:
python -m pip install --upgrade pip
pip install -r requirements.txt
# Or if using uv/pip-tools:
# pip install -e ".[dev]"
```

*Core backend dependencies planned:*
- `fastapi`, `uvicorn[standard]`
- `pydantic>=2.7`, `pydantic-settings`
- `sqlalchemy>=2.0`, `alembic>=1.13`, `asyncpg`, `psycopg2-binary`
- `celery>=5.3`, `redis>=5.0`
- `cryptography>=42.0` (for X.509 and ASN.1 parsing)
- `pytest`, `pytest-asyncio`, `pytest-cov`, `mypy`, `ruff`

---

## 5. Frontend Environment Setup

### 5.1 Node.js & Package Installation `[TARGET ARCHITECTURE / SPRINT 0]`

Once the frontend package manifest (`apps/web/package.json`) is introduced in Sprint 0:

```powershell
# Navigate to web application directory
cd apps/web

# Install frontend dependencies
pnpm install  # Or npm install
```

*Core frontend stack planned:*
- React 18, TypeScript 5.4+
- Vite (fast build & HMR)
- Tailwind CSS & Lucide Icons
- TanStack Query (React Query)
- Axios or Fetch client for typed API interactions

---

## 6. Docker & Local Infrastructure Services

The platform relies on PostgreSQL 16 (relational persistence and JSONB) and Redis 7 (broker and cache).

### 6.1 Docker Compose Services `[TARGET ARCHITECTURE / SPRINT 0]`

Sprint 0 introduces `infra/docker/docker-compose.yml`. To start the backing services:

```powershell
# Planned command to launch local PostgreSQL and Redis:
docker compose -f infra/docker/docker-compose.yml up -d

# Verify containers are healthy:
docker compose -f infra/docker/docker-compose.yml ps
```

*Service Ports (Local):*
- PostgreSQL: `localhost:5432` (User: `postgres`, Password: `postgres`, DB: `quantum_flow_dev`)
- Redis: `localhost:6379`

---

## 7. Environment Configuration

### 7.1 Create Local `.env` `[ACTIVE / WORKING NOW]`

A sanitized `.env.example` file is provided in the repository root. Copy it to `.env`:

#### Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

#### macOS / Linux:
```bash
cp .env.example .env
```

> [!CAUTION]
> - Never commit `.env` to Git. The `.gitignore` is pre-configured to ignore `.env`.
> - Do not insert production secrets or actual cloud keys into `.env`. Local defaults are pre-configured for safe offline development.

---

## 8. Database Migrations & Seeding

### 8.1 Alembic Migration Workflow `[TARGET ARCHITECTURE / SPRINT 1]`

When database schema and migrations are implemented in Sprint 1:

```powershell
# Run pending database migrations
alembic upgrade head

# Generate a new migration (after modifying models)
alembic revision --autogenerate -m "Add scan jobs table"

# Roll back the most recent migration
alembic downgrade -1
```

---

## 9. Running Local Development Services

### 9.1 FastAPI Backend `[TARGET ARCHITECTURE / SPRINT 0]`

```powershell
# Run backend with auto-reload
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```
Interactive API docs will be available at: `http://127.0.0.1:8000/docs`.

### 9.2 Celery Worker `[TARGET ARCHITECTURE / SPRINT 2]`

```powershell
# Start local scan worker
celery -A apps.worker.celery_app worker --loglevel=info --concurrency=2
```

### 9.3 React Frontend `[TARGET ARCHITECTURE / SPRINT 0]`

```powershell
cd apps/web
pnpm run dev
```
Web dashboard will be available at: `http://localhost:5173`.

---

## 10. Code Quality & Testing Commands

To maintain code standards, all code must pass linting, type checks, and tests before opening a pull request.

### 10.1 Planned Code Quality Suite `[TARGET ARCHITECTURE / SPRINT 0]`

```powershell
# Format and lint with Ruff
ruff format .
ruff check . --fix

# Static Type Checking with Mypy
mypy apps/ packages/

# Run Unit & Integration Tests with Pytest
pytest -v --cov=apps --cov=packages --cov-report=term-missing

# Frontend Lint and Type Check
cd apps/web
pnpm run lint
pnpm run typecheck
```

---

## 11. Windows Development Considerations

If developing on Microsoft Windows:
1. **Line Endings:** Git should be configured to preserve LF line endings:
   ```powershell
   git config --global core.autocrlf input
   ```
2. **Path Separators:** Always use `pathlib.Path` in Python code rather than string concatenation with `/` or `\` to ensure cross-platform compatibility.
3. **Docker on Windows:** Ensure Docker Desktop is configured to use the **WSL 2 backend** (Windows Subsystem for Linux 2) for optimal filesystem I/O performance.
4. **Celery on Windows:** Celery's default prefork process pool has known issues on Windows. For local Windows worker testing, pass `--pool=solo` or `--pool=threads`:
   ```powershell
   celery -A apps.worker.celery_app worker --pool=solo --loglevel=info
   ```

---

## 12. Troubleshooting Common Issues

| Issue | Cause | Solution |
|---|---|---|
| `Scripts\Activate.ps1 cannot be loaded` | PowerShell execution policy restricted | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| `Cannot connect to PostgreSQL on 5432` | Docker container not running or port conflict | Verify Docker is running: `docker ps`. Ensure local native Postgres isn't occupying port 5432. |
| `Redis connection refused on 6379` | Redis container stopped | Run `docker compose up -d redis` |
| `ModuleNotFoundError` during tests | Package not installed in editable mode | Run `pip install -e .` from repository root |
| `Line ending warnings in Git` | CRLF vs LF discrepancy | Check `.editorconfig` and run `git config core.autocrlf input` |

