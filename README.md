
# water — mini game store (FastAPI + PySide6 + Pygame)

Steam? Nah. **water.** Minimalistická semestrálka: API → launcher → „hra".
Používá **Poetry**, **Docker Compose** a pohodlný **Makefile**.

## ✨ Features

- 🔐 **JWT Authentication** - Secure login with access/refresh tokens (Argon2 hashing)
- 🎮 **Game Store** - Browse, purchase, and manage games
- 💾 **MinIO Storage** - S3-compatible game file storage with presigned URLs
- 🔒 **DRM System** - Launch tokens, session attestation, heartbeat mechanism
- 🖥️ **PySide6 Launcher** - Desktop client for browsing, downloading, and launching games
- 🎮 **Pygame Demo Game** - Example game with integrated DRM client
- 🐳 **Docker Compose** - PostgreSQL + MinIO + API

## 🚀 Quick Start

**TL;DR:**
```bash
make setup        # First time setup (builds, starts, seeds)
make run-launcher # Start the launcher
```

**Manual steps (if needed):**
```bash
make run-api-dev  # Start backend services
make seed-dev     # Seed demo data
make run-launcher # Run the launcher
```

**Login:** `admin / Admin1234` or `testuser / Test1234`

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
│        ├─ shop.py           # Store & purchases
│        ├─ drm.py            # Launch tokens
│        └─ sessions.py       # Session management
├─ water_client/              # PySide6 Launcher
│  ├─ pyproject.toml
│  └─ launcher/
│     ├─ __main__.py          # Main launcher app (Qt GUI)
│     ├─ config.py            # API URL configuration
│     └─ download.py          # Download manager with progress
└─ game_skeleton/             # Pygame Demo Game
   ├─ pyproject.toml
   └─ demo_game/
      ├─ __main__.py          # Game with DRM integration
      └─ drm.py               # DRM client (WaterDRM class)
```

## 🎮 Demo Game

The demo game showcases full DRM integration:
- **Launch token** validation on startup
- **Session attestation** with the server
- **Heartbeat** every 30 seconds to maintain session
- **Graceful shutdown** if DRM validation fails

```bash
# The game is launched through the launcher with proper DRM tokens
# Manual launch (for testing) requires valid tokens:
cd ~/.water/games/demo-game/1.0.0/extracted
python -m demo_game --token <launch_token> --access <access_token> --api http://127.0.0.1:8080
```

## 🛠️ Development Commands

### Docker Services

```bash
make build-api-dev    # Build API Docker image
make run-api-dev      # Start all services (PostgreSQL + MinIO + API)
make restart-api-dev  # Restart API container
make logs-api-dev     # View logs
make stop-api-dev     # Stop all services
```

### Launcher

```bash
make install-launcher # Install launcher dependencies
make run-launcher     # Run the launcher
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
| **Client** | PySide6 6.x (Qt for Python) |
| **Game Engine** | Pygame 2.x |
| **Dev Tools** | Ruff (linter/formatter), mypy (type checker) |
| **Deployment** | Docker Compose |

## 🔒 DRM Flow

```
1. User clicks "Play" in launcher
2. Launcher requests launch token: POST /launch/{build_id}
3. API validates entitlement → returns JWT launch token (valid 10 min)
4. Launcher starts game with --token and --access flags
5. Game calls POST /sessions/attest with launch token
6. API creates session, returns session_id
7. Game sends heartbeat every 30s: POST /sessions/{id}/heartbeat
8. If heartbeat fails or session expires → game terminates
```

## 🔧 Configuration

Edit `water_api/dev.env`:

```env
DATABASE_URL=postgresql+psycopg2://water-app:waterpass@db:5432/waterdb
JWT_SECRET=dev-secret-key-change-in-production
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=water-games
```


## 🎓 Project Context

Semestrální projekt - alternativa k Steam/GOG s vlastním DRM systémem.
Zaměření na kybernetickou bezpečnost a distribuci softwaru.
