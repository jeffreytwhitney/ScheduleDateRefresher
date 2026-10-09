import os

from dotenv import load_dotenv

load_dotenv()


def get_env_value(key: str, default: str = "") -> str:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def get_logger_level_key(logger_name: str) -> str:
    return f"LOG_LEVEL_{logger_name.upper()}"
