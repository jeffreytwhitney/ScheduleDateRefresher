import os

from dotenv import load_dotenv

import sys
from pathlib import Path

_APP_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
load_dotenv(_APP_DIR / '.env')


ENV_PREFIX = "SDR_"


def get_env_value(key: str, default: str = "") -> str:
    value = os.getenv(ENV_PREFIX + key)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def get_logger_level_key(logger_name: str) -> str:
    return f"LOG_LEVEL_{logger_name.upper()}"
