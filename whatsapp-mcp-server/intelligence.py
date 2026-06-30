# whatsapp-mcp-server/intelligence.py
"""On-demand, allowlist-scoped chat intelligence via the Anthropic SDK.

The LLM call is injected (generate_text / generate_json) so this module is
fully testable without a network or API key.
"""
import json
import os
import re

MODEL = os.environ.get("WHATSAPP_DASHBOARD_MODEL", "claude-opus-4-8")

SUMMARY_SYSTEM = (
    "You summarize a single WhatsApp chat in one or two sentences. "
    "Be concrete and neutral. Output only the summary text."
)
SUGGEST_SYSTEM = (
    "You draft a short, natural reply for chats that appear to have an "
    "unanswered message addressed to the user. Return a JSON array of objects "
    'with keys "chat_jid", "context" (why a reply is suggested), and "draft". '
    "Only include chats that genuinely need a reply; return [] if none."
)
REMINDERS_SYSTEM = (
    "You find reminders across the user's allowlisted WhatsApp chats: "
    "unanswered questions to the user, and missed events (birthdays, "
    "anniversaries). Return a JSON array of objects with keys \"kind\", "
    '"text", "related_chat_jid", "suggested_action". Return [] if none.'
)


def gather(allowlist: dict, fetch_fn) -> dict:
    out = {}
    for jid in allowlist:
        text = fetch_fn(jid)
        if text and text.strip():
            out[jid] = text
    return out


def summarize(allowlist: dict, fetch_fn, generate_text) -> list:
    results = []
    for jid, text in gather(allowlist, fetch_fn).items():
        user = f"Chat label: {allowlist[jid]['label']}\n\nMessages:\n{text}"
        results.append({
            "chat_jid": jid,
            "label": allowlist[jid]["label"],
            "summary": generate_text(SUMMARY_SYSTEM, user),
        })
    return results


def _labeled_corpus(allowlist: dict, gathered: dict) -> str:
    blocks = []
    for jid, text in gathered.items():
        blocks.append(f"### {allowlist[jid]['label']} (jid: {jid})\n{text}")
    return "\n\n".join(blocks)


def suggest(allowlist: dict, fetch_fn, generate_json) -> list:
    gathered = gather(allowlist, fetch_fn)
    if not gathered:
        return []
    raw = generate_json(SUGGEST_SYSTEM, _labeled_corpus(allowlist, gathered))
    items = raw if isinstance(raw, list) else raw.get("items", [])
    out = []
    for it in items:
        jid = it.get("chat_jid") or next(iter(gathered))
        out.append({
            "chat_jid": jid,
            "label": allowlist.get(jid, {}).get("label", jid),
            "context": it.get("context", ""),
            "draft": it.get("draft", ""),
        })
    return out


def reminders(allowlist: dict, fetch_fn, generate_json) -> list:
    gathered = gather(allowlist, fetch_fn)
    if not gathered:
        return []
    raw = generate_json(REMINDERS_SYSTEM, _labeled_corpus(allowlist, gathered))
    items = raw if isinstance(raw, list) else raw.get("items", [])
    return [{
        "kind": it.get("kind", "reminder"),
        "text": it.get("text", ""),
        "related_chat_jid": it.get("related_chat_jid"),
        "suggested_action": it.get("suggested_action", ""),
    } for it in items]


class IntelligenceUnavailable(Exception):
    """Raised when the Anthropic API is not configured or rejects auth."""


def _extract_json(text: str):
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    payload = fence.group(1).strip() if fence else text.strip()
    try:
        return json.loads(payload)
    except (json.JSONDecodeError, ValueError):
        return []


def make_generators(client=None):
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise IntelligenceUnavailable("ANTHROPIC_API_KEY is not set")
        import anthropic
        client = anthropic.Anthropic()

    def _call(system, user):
        resp = client.messages.create(
            model=MODEL, max_tokens=2000, system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")

    def generate_text(system, user):
        return _call(system, user).strip()

    def generate_json(system, user):
        return _extract_json(_call(system, user))

    return generate_text, generate_json
