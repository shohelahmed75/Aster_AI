"""
config.py — Loads settings from .env (secrets) and config.json (everything else).
"""

import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the project root (two levels up from this file)
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

# ─── Load config.json ────────────────────────────────────────────────────────────
_config_file = _project_root / "config.json"
_config = {}
if _config_file.exists():
    try:
        with open(_config_file, "r", encoding="utf-8") as f:
            _config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"⚠️  Invalid config.json: {e}")

# ─── Secrets (from .env) ─────────────────────────────────────────────────────────
API_KEY = os.getenv("API_KEY", "")
CLIENT_SECRET_FILE = str(_project_root / os.getenv("CLIENT_SECRET_FILE", "client_secret.json"))
TOKEN_FILE = str(_project_root / "token.json")

# ─── Bot Settings (from config.json) ─────────────────────────────────────────────
CHANNEL_ID = _config.get("channel_id", "")
VIDEO_ID = _config.get("video_id", "")
BOT_PREFIX = _config.get("bot_prefix", "/")
WELCOME_MESSAGE = _config.get("welcome_message", "Welcome to the stream, {username}! 🎉")
POLL_DURATION = int(_config.get("poll_duration", 5))
COOLDOWN_SECONDS = int(_config.get("cooldown_seconds", 5))

# ─── API Scopes ──────────────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/youtube"]

# ─── File Paths ──────────────────────────────────────────────────────────────────
DATA_DIR = str(_project_root / _config.get("data_dir", "data"))
COMMANDS_FILE = str(_project_root / "commands.json")
LOG_FILE = os.path.join(DATA_DIR, "bot.log")
