# whatsapp-mcp-server/allowlist.py
import json
import os


class AllowlistError(Exception):
    """Raised when the allowlist file is missing, malformed, or has invalid entries."""


VALID_MODES = ("read", "read+send")
DEFAULT_MODE = "read+send"


def load_allowlist(path: str) -> dict[str, dict]:
    """Load the allowlist as {jid: {"label": str, "mode": str}}.

    An entry without a "mode" defaults to "read+send" (backward compatible).
    Fails closed on a missing/malformed file or an invalid mode value.
    """
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

    result: dict[str, dict] = {}
    for entry in chats:
        if not isinstance(entry, dict) or "jid" not in entry:
            raise AllowlistError(f"Allowlist entry missing 'jid': {entry!r}")
        mode = entry.get("mode", DEFAULT_MODE)
        if mode not in VALID_MODES:
            raise AllowlistError(
                f"Allowlist entry {entry['jid']} has invalid mode {mode!r}; "
                f"must be one of {VALID_MODES}."
            )
        result[entry["jid"]] = {"label": entry.get("label", entry["jid"]), "mode": mode}
    return result


def is_allowed(jid: str, allowlist: dict[str, dict]) -> bool:
    """Membership = readable. Every allowlisted chat is readable."""
    return jid in allowlist


def can_send(jid: str, allowlist: dict[str, dict]) -> bool:
    """A chat is sendable only if it is allowlisted AND its mode is read+send."""
    return jid in allowlist and allowlist[jid]["mode"] == "read+send"


def normalize_recipient(recipient: str) -> str:
    if "@" in recipient:
        if recipient.endswith("@s.whatsapp.net") or recipient.endswith("@g.us"):
            return recipient
        raise AllowlistError(f"{recipient!r} is not a valid WhatsApp JID.")
    digits = recipient.removeprefix("+").replace(" ", "").replace("-", "")
    if digits and all(c in "0123456789" for c in digits):
        return f"{digits}@s.whatsapp.net"
    raise AllowlistError(
        f"Cannot interpret recipient {recipient!r} as a phone number or JID."
    )


def check_send(recipient: str, allowlist: dict[str, dict]) -> str:
    jid = normalize_recipient(recipient)
    if not is_allowed(jid, allowlist):
        raise AllowlistError(
            f"{jid} is not in the allowlist; add it with manage_allowlist.py."
        )
    if not can_send(jid, allowlist):
        raise AllowlistError(
            f"{jid} is read-only; mark it read+send to allow sending."
        )
    return jid


def filter_chats(chats: list, allowlist: dict[str, str]) -> list:
    return [c for c in chats if is_allowed(c.jid, allowlist)]


def filter_messages(messages: list, allowlist: dict[str, str]) -> list:
    return [m for m in messages if is_allowed(m.chat_jid, allowlist)]


def filter_contacts(contacts: list, allowlist: dict[str, str]) -> list:
    return [c for c in contacts if is_allowed(c.jid, allowlist)]
