"""Tiny on-disk cache for dashboard intelligence sections."""
import json
import os
from datetime import datetime, timezone


def load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def get_section(path: str, name: str):
    return load(path).get(name)


def put_section(path: str, name: str, data) -> dict:
    cache = load(path)
    section = {"generated_at": datetime.now(timezone.utc).isoformat(), "data": data}
    cache[name] = section
    try:
        with open(path, "w") as f:
            json.dump(cache, f)
    except (OSError, TypeError):
        pass  # best-effort cache; never break a request on a write/serialize failure
    return section
