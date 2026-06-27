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


def normalize_recipient(recipient: str) -> str:
    if "@" in recipient:
        if recipient.endswith("@s.whatsapp.net") or recipient.endswith("@g.us"):
            return recipient
        raise AllowlistError(f"{recipient!r} is not a valid WhatsApp JID.")
    digits = recipient.lstrip("+").replace(" ", "").replace("-", "")
    if digits and all(c in "0123456789" for c in digits):
        return f"{digits}@s.whatsapp.net"
    raise AllowlistError(
        f"Cannot interpret recipient {recipient!r} as a phone number or JID."
    )


def check_send(recipient: str, allowlist: dict[str, str]) -> str:
    jid = normalize_recipient(recipient)
    if not is_allowed(jid, allowlist):
        raise AllowlistError(
            f"{jid} is not in the allowlist; add it with manage_allowlist.py."
        )
    return jid
