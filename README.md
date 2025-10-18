
# water — mini game store (FastAPI + PySide6 + Pygame)

Steam? Nah. **water.** Minimalistická semestrálka: API → launcher → „hra“.
Používá **Poetry** a pohodlný **Makefile**.

## Makefile targets (nejpoužívanější)
```bash
make infra-up          # spustí Postgres v Dockeru
make backend-setup     # poetry install pro backend
make backend-seed      # vytvoří tabulky + demo data
make backend-run       # uvicorn s reloadem
make client-setup      # poetry install pro launcher
make client-run        # spustí PySide6 launcher
make game-setup        # poetry install pro hru
make game-run          # spustí demo hru s DUMMY tokenem
make fmt               # black + ruff (všude)
make infra-down        # stopne postgres
```

**Demo účet:** `test@example.com` / `test`  
API: http://127.0.0.1:8000 (Swagger na /docs)

## Struktura
```
water/
├─ Makefile
├─ infra/
│  └─ docker-compose.yml
├─ backend/          # FastAPI (Poetry)
│  ├─ pyproject.toml
│  └─ app/{main.py, db.py, models.py, security.py, api/*, seed.py}
├─ client/           # PySide6 (Poetry)
│  ├─ pyproject.toml
│  └─ launcher/{__main__.py, config.py}
└─ game_skeleton/    # Pygame (Poetry)
   ├─ pyproject.toml
   └─ demo_game/__main__.py
```

## Rychlý start
```bash
make infra-up
make backend-setup backend-seed backend-run  # v jiném terminálu
make client-setup client-run                 # další terminál
```

### Pozn.
- DB je cíleně Postgres (docker compose). Pokud chceš SQLite pro vývoj, změň `DATABASE_URL` v `backend/.env` nebo `app/db.py`.
- Build/download endpoint a verifikaci SHA-256 můžeš dopsat později.
