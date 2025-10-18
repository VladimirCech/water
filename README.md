
# water — mini game store (FastAPI + PySide6 + Pygame)

Steam? Nah. **water.** Minimalistická semestrálka: API → launcher → „hra".
Používá **Poetry**, **Docker Compose** a pohodlný **Makefile**.

## ✨ Features

- 🔐 **JWT Authentication** - Secure login with access/refresh tokens
- 🎮 **Game Catalog** - Browse and manage games
- 💾 **MinIO Storage** - S3-compatible game file storage
- 🔒 **DRM System** - Session management with heartbeat mechanism
- 🖥️ **PySide6 Launcher** - Desktop client for game management
- 🐳 **Docker Compose** - PostgreSQL + MinIO + API

## 🚀 Quick Start

```bash
# Build and start services
make build-dev
make run-api-dev

# Check logs
make logs-api-dev

# Stop services
make stop-api-dev
```

**API:** http://localhost:8080 (Swagger docs: `/docs`)  
**MinIO Console:** http://localhost:9001 (minioadmin / minioadmin)

## 📁 Struktura

```
water/
├─ Makefile
├─ compose/
│  └─ docker-compose.yml      # PostgreSQL + MinIO + API
├─ water_api/                 # FastAPI Backend
│  ├─ Dockerfile
│  ├─ pyproject.toml
│  ├─ dev.env                 # Environment variables
│  └─ app/
│     ├─ main.py              # FastAPI app
│     ├─ db.py                # Database connection
│     ├─ models.py            # SQLAlchemy models
│     ├─ security.py          # JWT & auth
│     ├─ storage.py           # MinIO S3 client
│     ├─ seed.py              # Demo data
│     └─ api/                 # API routes
│        ├─ auth.py           # Login/register
│        ├─ games.py          # Game catalog
│        ├─ drm.py            # Launch tokens
│        └─ sessions.py       # Session management
├─ water_client/              # PySide6 Launcher (TODO)
│  ├─ pyproject.toml
│  └─ launcher/
└─ game_skeleton/             # Pygame Template (TODO)
   ├─ pyproject.toml
   └─ demo_game/
```

## 🛠️ Development Commands

### Docker Services

```bash
make build-dev        # Build API Docker image
make run-api-dev      # Start all services (PostgreSQL + MinIO + API)
make restart-api-dev  # Restart API container
make logs-api-dev     # View logs
make stop-api-dev     # Stop all services
```

### Code Quality

```bash
make fmt              # Format with Ruff
make lint             # Lint with Ruff
make type-check       # Type check with mypy
make check            # Run all checks
make test             # Run tests
```

## 📚 API Endpoints

### Authentication
- `POST /auth/login` - Login with email/password → returns JWT tokens

### Games
- `GET /games/` - List user's games (requires auth)
- `GET /games/builds/{build_id}/download` - Get presigned download URL

### DRM
- `POST /launch/{build_id}` - Get launch token (requires entitlement)

### Sessions
- `POST /sessions/attest` - Start game session with launch token
- `POST /sessions/{session_id}/heartbeat` - Keep session alive (30s interval)

### Health
- `GET /healthz` - Health check

## 🏗️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI 0.115, Pydantic 2.8, SQLAlchemy 2.0 |
| **Database** | PostgreSQL 17 |
| **Storage** | MinIO (S3-compatible) with boto3 |
| **Auth** | JWT (PyJWT), Argon2 password hashing |
| **Client** | PySide6 (Qt for Python) - TODO |
| **Game Engine** | Pygame - TODO |
| **Dev Tools** | Ruff (linter/formatter), mypy (type checker) |
| **Deployment** | Docker Compose |

## 🔧 Configuration

Edit `water_api/dev.env`:

```env
DATABASE_URL=postgresql+psycopg2://water-app:waterpass@db:5432/waterdb
JWT_SECRET=dev-secret-key-change-in-production
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=water-games
```

## 📝 Notes

- Demo user seed script TODO
- Game upload endpoint in progress
- SHA-256 verification for downloads planned
- PySide6 launcher implementation pending
- Pygame game skeleton with DRM integration coming soon

## 🎓 Project Context

Semestrální projekt - alternativa k Steam/GOG s vlastním DRM systémem.
Zaměření na kybernetickou bezpečnost a distribuci softwaru.
