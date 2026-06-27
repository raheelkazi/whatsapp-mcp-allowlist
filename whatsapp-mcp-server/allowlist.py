# whatsapp-mcp-server/allowlist.py
import json
import os


class AllowlistError(Exception):
    """Raised when the allowlist cannot be loaded or a target is not allowed."""


def load_allowlist(path: str) -> dict[str, str]:
    if not os.path.exists(path):
        raise AllowlistError(
            f"Allowlist not found at {path}. Create it with manage_allowlist.py."
        )
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise AllowlistError(f"Allowlist at {path} is unreadable: {e}")

    chats = data.get("chats") if isinstance(data, dict) else None
    if not isinstance(chats, list):
        raise AllowlistError("Allowlist must be an object with a 'chats' list.")

    result: dict[str, str] = {}
    for entry in chats:
        if not isinstance(entry, dict) or "jid" not in entry:
            raise AllowlistError(f"Allowlist entry missing 'jid': {entry!r}")
        result[entry["jid"]] = entry.get("label", entry["jid"])
    return result


def is_allowed(jid: str, allowlist: dict[str, str]) -> bool:
    return jid in allowlist
