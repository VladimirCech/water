from pathlib import Path

API_BASE = "http://127.0.0.1:8080"

# Local storage paths
DATA_DIR = Path.home() / ".water"
GAMES_DIR = DATA_DIR / "games"
CACHE_DIR = DATA_DIR / "cache"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
GAMES_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
