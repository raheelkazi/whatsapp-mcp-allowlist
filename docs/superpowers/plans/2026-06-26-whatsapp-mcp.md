# WhatsApp MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A locally-run WhatsApp MCP server that lets Claude Code agents read and send messages on the user's personal WhatsApp, scoped to an explicit allowlist of specific people and groups, with every send gated by a human confirmation.

**Architecture:** Fork `lharries/whatsapp-mcp` (Go `whatsmeow` bridge + Python FastMCP server + SQLite). Add a new `allowlist.py` guard module in the Python server that (a) post-filters every read tool to allowlisted JIDs and (b) rejects sends to non-allowlisted JIDs before they reach the bridge. Confirmation on send is delegated to Claude Code's native permission prompt (send tools are not auto-approved). A standalone `manage_allowlist.py` CLI — never exposed over MCP — lets the user search the full contact/chat tables to discover JIDs and curate the allowlist.

**Tech Stack:** Go (`whatsmeow`), Python 3.6+ with `uv`, FastMCP, SQLite, pytest.

## Global Constraints

- Python tool functions live in `whatsapp-mcp-server/`; the guard is `whatsapp-mcp-server/allowlist.py`.
- Allowlist file path: `whatsapp-mcp-server/allowed_chats.json` (gitignored; already in `.gitignore`).
- JID forms: people are `<digits>@s.whatsapp.net`, groups are `<digits>@g.us`.
- **Fail-closed:** a missing or malformed allowlist file must raise `AllowlistError` (server refuses to start). Never default to "all allowed".
- The Go bridge listens on `http://localhost:8080`. Bridge endpoints and SQLite schema are inherited unchanged — do not modify `whatsapp-bridge/`.
- Upstream dataclasses (in `whatsapp.py`) — do not change their fields:
  - `Chat`: `.jid`, `.name`, `.last_message_time`, `.last_message`, `.last_sender`, `.last_is_from_me`; property `.is_group`.
  - `Message`: `.timestamp`, `.sender`, `.content`, `.is_from_me`, `.chat_jid`, `.id`, `.chat_name`, `.media_type`.
  - `Contact`: `.phone_number`, `.name`, `.jid`.
- TDD throughout. Commit after every task. DRY, YAGNI.

---

### Task 1: Fork and vendor the upstream project; verify it builds

**Files:**
- Create: `whatsapp-bridge/` (cloned from upstream)
- Create: `whatsapp-mcp-server/` (cloned from upstream)

**Interfaces:**
- Produces: the upstream codebase in place — `whatsapp-mcp-server/main.py`, `whatsapp-mcp-server/whatsapp.py`, `whatsapp-mcp-server/pyproject.toml`, `whatsapp-bridge/main.go`.

- [ ] **Step 1: Clone upstream into a temp dir and copy the two component folders in**

```bash
cd /Users/raheelkazi/Speechify/code/whatsapp-mcp
git clone --depth 1 https://github.com/lharries/whatsapp-mcp /tmp/wa-upstream
cp -R /tmp/wa-upstream/whatsapp-bridge ./whatsapp-bridge
cp -R /tmp/wa-upstream/whatsapp-mcp-server ./whatsapp-mcp-server
rm -rf /tmp/wa-upstream ./whatsapp-bridge/.git ./whatsapp-mcp-server/.git
```

- [ ] **Step 2: Verify the Go bridge compiles**

Run: `cd whatsapp-bridge && go build -o /dev/null . && cd ..`
Expected: exits 0, no output. (On macOS CGO for SQLite is on by default; if it errors about a C compiler, install Xcode CLI tools: `xcode-select --install`.)

- [ ] **Step 3: Verify the Python server's deps resolve**

Run: `cd whatsapp-mcp-server && uv sync && uv run python -c "import main" && cd ..`
Expected: `uv sync` installs deps; the import prints nothing and exits 0.

- [ ] **Step 4: Add a pytest dev dependency and a tests package**

```bash
cd whatsapp-mcp-server
uv add --dev pytest
mkdir -p tests
touch tests/__init__.py
cd ..
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: vendor lharries/whatsapp-mcp as foundation"
```

---

### Task 2: Allowlist loader and membership check

**Files:**
- Create: `whatsapp-mcp-server/allowlist.py`
- Test: `whatsapp-mcp-server/tests/test_allowlist.py`

**Interfaces:**
- Produces:
  - `class AllowlistError(Exception)`
  - `load_allowlist(path: str) -> dict[str, str]` — returns `{jid: label}`. Raises `AllowlistError` if the file is missing, is not valid JSON, or lacks a `"chats"` list of `{"jid", "label"}` objects.
  - `is_allowed(jid: str, allowlist: dict[str, str]) -> bool`

- [ ] **Step 1: Write the failing tests**

```python
# whatsapp-mcp-server/tests/test_allowlist.py
import json
import pytest
from allowlist import load_allowlist, is_allowed, AllowlistError


def write(tmp_path, obj):
    p = tmp_path / "allowed_chats.json"
    p.write_text(json.dumps(obj))
    return str(p)


def test_load_returns_jid_to_label_map(tmp_path):
    path = write(tmp_path, {"chats": [
        {"jid": "111@s.whatsapp.net", "label": "Mom"},
        {"jid": "222@g.us", "label": "Family"},
    ]})
    assert load_allowlist(path) == {
        "111@s.whatsapp.net": "Mom",
        "222@g.us": "Family",
    }


def test_missing_file_fails_closed(tmp_path):
    with pytest.raises(AllowlistError):
        load_allowlist(str(tmp_path / "nope.json"))


def test_malformed_json_fails_closed(tmp_path):
    p = tmp_path / "allowed_chats.json"
    p.write_text("{not json")
    with pytest.raises(AllowlistError):
        load_allowlist(str(p))


def test_wrong_shape_fails_closed(tmp_path):
    path = write(tmp_path, {"chats": [{"label": "no jid"}]})
    with pytest.raises(AllowlistError):
        load_allowlist(path)


def test_empty_allowlist_is_valid_but_allows_nothing(tmp_path):
    path = write(tmp_path, {"chats": []})
    al = load_allowlist(path)
    assert al == {}
    assert is_allowed("111@s.whatsapp.net", al) is False


def test_is_allowed_membership():
    al = {"111@s.whatsapp.net": "Mom"}
    assert is_allowed("111@s.whatsapp.net", al) is True
    assert is_allowed("999@s.whatsapp.net", al) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd whatsapp-mcp-server && uv run pytest tests/test_allowlist.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'allowlist'`.

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd whatsapp-mcp-server && uv run pytest tests/test_allowlist.py -v`
Expected: PASS — 6 passed.

- [ ] **Step 5: Commit**

```bash
git add whatsapp-mcp-server/allowlist.py whatsapp-mcp-server/tests/test_allowlist.py
git commit -m "feat: fail-closed allowlist loader and membership check"
```

---

### Task 3: Recipient normalization and send check

**Files:**
- Modify: `whatsapp-mcp-server/allowlist.py`
- Test: `whatsapp-mcp-server/tests/test_allowlist.py`

**Interfaces:**
- Consumes: `is_allowed`, `AllowlistError` from Task 2.
- Produces:
  - `normalize_recipient(recipient: str) -> str` — a bare digit string becomes `<digits>@s.whatsapp.net`; a value already containing `@` is returned unchanged; anything else raises `AllowlistError`.
  - `check_send(recipient: str, allowlist: dict[str, str]) -> str` — normalizes `recipient`, raises `AllowlistError` if the resulting JID is not allowed, otherwise returns the normalized JID.

- [ ] **Step 1: Write the failing tests (append to test file)**

```python
# append to whatsapp-mcp-server/tests/test_allowlist.py
from allowlist import normalize_recipient, check_send


def test_normalize_bare_phone_becomes_user_jid():
    assert normalize_recipient("1234567890") == "1234567890@s.whatsapp.net"


def test_normalize_passes_through_existing_jid():
    assert normalize_recipient("111@s.whatsapp.net") == "111@s.whatsapp.net"
    assert normalize_recipient("222@g.us") == "222@g.us"


def test_normalize_rejects_garbage():
    with pytest.raises(AllowlistError):
        normalize_recipient("not a number")


def test_check_send_allows_listed_target():
    al = {"1234567890@s.whatsapp.net": "Mom"}
    assert check_send("1234567890", al) == "1234567890@s.whatsapp.net"


def test_check_send_rejects_unlisted_target():
    al = {"1234567890@s.whatsapp.net": "Mom"}
    with pytest.raises(AllowlistError):
        check_send("999@s.whatsapp.net", al)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd whatsapp-mcp-server && uv run pytest tests/test_allowlist.py -k "normalize or check_send" -v`
Expected: FAIL — `ImportError: cannot import name 'normalize_recipient'`.

- [ ] **Step 3: Add the implementation to `allowlist.py`**

```python
# append to whatsapp-mcp-server/allowlist.py

def normalize_recipient(recipient: str) -> str:
    if "@" in recipient:
        return recipient
    digits = recipient.lstrip("+").replace(" ", "").replace("-", "")
    if digits.isdigit():
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd whatsapp-mcp-server && uv run pytest tests/test_allowlist.py -v`
Expected: PASS — 11 passed.

- [ ] **Step 5: Commit**

```bash
git add whatsapp-mcp-server/allowlist.py whatsapp-mcp-server/tests/test_allowlist.py
git commit -m "feat: recipient normalization and send allowlist check"
```

---

### Task 4: Read filters for chats, messages, and contacts

**Files:**
- Modify: `whatsapp-mcp-server/allowlist.py`
- Test: `whatsapp-mcp-server/tests/test_allowlist.py`

**Interfaces:**
- Consumes: `is_allowed` from Task 2.
- Produces (each preserves input order, drops non-allowlisted items):
  - `filter_chats(chats: list, allowlist: dict[str, str]) -> list` — keeps items whose `.jid` is allowed.
  - `filter_messages(messages: list, allowlist: dict[str, str]) -> list` — keeps items whose `.chat_jid` is allowed.
  - `filter_contacts(contacts: list, allowlist: dict[str, str]) -> list` — keeps items whose `.jid` is allowed.

- [ ] **Step 1: Write the failing tests (append to test file)**

```python
# append to whatsapp-mcp-server/tests/test_allowlist.py
from dataclasses import dataclass
from allowlist import filter_chats, filter_messages, filter_contacts


@dataclass
class FakeChat:
    jid: str


@dataclass
class FakeMessage:
    chat_jid: str


@dataclass
class FakeContact:
    jid: str


def test_filter_chats_keeps_only_allowed():
    al = {"111@s.whatsapp.net": "Mom"}
    chats = [FakeChat("111@s.whatsapp.net"), FakeChat("999@s.whatsapp.net")]
    assert filter_chats(chats, al) == [FakeChat("111@s.whatsapp.net")]


def test_filter_messages_keeps_only_allowed_chat():
    al = {"111@s.whatsapp.net": "Mom"}
    msgs = [FakeMessage("111@s.whatsapp.net"), FakeMessage("999@s.whatsapp.net")]
    assert filter_messages(msgs, al) == [FakeMessage("111@s.whatsapp.net")]


def test_filter_contacts_keeps_only_allowed():
    al = {"111@s.whatsapp.net": "Mom"}
    contacts = [FakeContact("111@s.whatsapp.net"), FakeContact("999@s.whatsapp.net")]
    assert filter_contacts(contacts, al) == [FakeContact("111@s.whatsapp.net")]


def test_filters_handle_empty_allowlist():
    assert filter_chats([FakeChat("111@s.whatsapp.net")], {}) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd whatsapp-mcp-server && uv run pytest tests/test_allowlist.py -k filter -v`
Expected: FAIL — `ImportError: cannot import name 'filter_chats'`.

- [ ] **Step 3: Add the implementation to `allowlist.py`**

```python
# append to whatsapp-mcp-server/allowlist.py

def filter_chats(chats: list, allowlist: dict[str, str]) -> list:
    return [c for c in chats if is_allowed(c.jid, allowlist)]


def filter_messages(messages: list, allowlist: dict[str, str]) -> list:
    return [m for m in messages if is_allowed(m.chat_jid, allowlist)]


def filter_contacts(contacts: list, allowlist: dict[str, str]) -> list:
    return [c for c in contacts if is_allowed(c.jid, allowlist)]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd whatsapp-mcp-server && uv run pytest tests/test_allowlist.py -v`
Expected: PASS — 15 passed.

- [ ] **Step 5: Commit**

```bash
git add whatsapp-mcp-server/allowlist.py whatsapp-mcp-server/tests/test_allowlist.py
git commit -m "feat: read filters for chats, messages, contacts"
```

---

### Task 5: Wire read guards into the MCP tools; trim deferred read tools; add `list_allowed_chats`

**Files:**
- Modify: `whatsapp-mcp-server/main.py`
- Test: `whatsapp-mcp-server/tests/test_tools_read.py`

**Interfaces:**
- Consumes: `load_allowlist`, `filter_chats`, `filter_messages`, `filter_contacts`, `is_allowed`, `AllowlistError` from Tasks 2 and 4; upstream `whatsapp.*` query functions.
- Produces: a module-level `ALLOWLIST` loaded at import; read tools that return allowlisted-only results; a new `list_allowed_chats()` tool; removal of `get_direct_chat_by_contact`, `get_contact_chats`, `get_last_interaction` tools.

Context: in upstream `main.py`, each tool imports a same-named function from the `whatsapp` module and returns its result. We add a guard at the top of the module and edit each read tool to filter before returning. `list_messages` can return a formatted string when `include_context` is set; to keep filtering reliable we always filter the underlying `Message`/`Chat`/`Contact` objects returned by the `whatsapp.*` query functions *before* any formatting.

- [ ] **Step 1: Write the failing test**

```python
# whatsapp-mcp-server/tests/test_tools_read.py
import importlib
from dataclasses import dataclass
import pytest


@dataclass
class FakeChat:
    jid: str
    name: str = ""


@pytest.fixture
def main_with_allowlist(tmp_path, monkeypatch):
    path = tmp_path / "allowed_chats.json"
    path.write_text('{"chats":[{"jid":"111@s.whatsapp.net","label":"Mom"}]}')
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(path))
    import main
    importlib.reload(main)
    return main


def test_list_chats_filters_to_allowlist(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    monkeypatch.setattr(main, "whatsapp_list_chats", lambda **kw: [
        FakeChat("111@s.whatsapp.net", "Mom"),
        FakeChat("999@s.whatsapp.net", "Stranger"),
    ])
    result = main.list_chats()
    assert [c.jid for c in result] == ["111@s.whatsapp.net"]


def test_list_allowed_chats_returns_entries(main_with_allowlist):
    result = main_with_allowlist.list_allowed_chats()
    assert result == [{"jid": "111@s.whatsapp.net", "label": "Mom"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd whatsapp-mcp-server && uv run pytest tests/test_tools_read.py -v`
Expected: FAIL — `AttributeError` / the tools are unfiltered or `list_allowed_chats` missing.

- [ ] **Step 3: Add the guard preamble near the top of `main.py`**

Add after the existing imports (the upstream file imports the query functions from `whatsapp`; alias them so tools can be tested by monkeypatching `main.whatsapp_list_chats` etc.):

```python
import os
from allowlist import (
    load_allowlist,
    filter_chats,
    filter_messages,
    filter_contacts,
    is_allowed,
    AllowlistError,
)

ALLOWLIST_PATH = os.environ.get(
    "WHATSAPP_ALLOWLIST_PATH",
    os.path.join(os.path.dirname(__file__), "allowed_chats.json"),
)
# Fail-closed: if this raises, the server does not start.
ALLOWLIST = load_allowlist(ALLOWLIST_PATH)
```

In the upstream file the query functions are imported like
`from whatsapp import list_chats as whatsapp_list_chats` (and similarly for
`list_messages`, `get_chat`, `get_message_context`, `search_contacts`). Confirm
these aliases exist; if a function is imported under its bare name, rename the import
to the `whatsapp_<name>` alias so the tool wrapper and its monkeypatch target match.

- [ ] **Step 4: Edit each read tool to filter before returning**

`list_chats` — filter the result:

```python
@mcp.tool()
def list_chats(query=None, limit=20, page=0, include_last_message=True, sort_by="last_active"):
    chats = whatsapp_list_chats(query=query, limit=limit, page=page,
                                include_last_message=include_last_message, sort_by=sort_by)
    return filter_chats(chats, ALLOWLIST)
```

`get_chat` — return only if allowed:

```python
@mcp.tool()
def get_chat(chat_jid: str, include_last_message: bool = True):
    if not is_allowed(chat_jid, ALLOWLIST):
        return {"error": f"{chat_jid} is not in the allowlist."}
    return whatsapp_get_chat(chat_jid, include_last_message)
```

`list_messages` — reject an explicit off-list `chat_jid`, otherwise filter the
underlying messages before any formatting:

```python
@mcp.tool()
def list_messages(after=None, before=None, sender_phone_number=None, chat_jid=None,
                  query=None, limit=20, page=0, include_context=True,
                  context_before=1, context_after=1):
    if chat_jid is not None and not is_allowed(chat_jid, ALLOWLIST):
        return {"error": f"{chat_jid} is not in the allowlist."}
    messages = whatsapp_list_messages(
        after=after, before=before, sender_phone_number=sender_phone_number,
        chat_jid=chat_jid, query=query, limit=limit, page=page,
        include_context=include_context, context_before=context_before,
        context_after=context_after)
    return filter_messages(messages, ALLOWLIST)
```

`get_message_context` — filter target and surrounding messages:

```python
@mcp.tool()
def get_message_context(message_id: str, before: int = 5, after: int = 5):
    ctx = whatsapp_get_message_context(message_id, before, after)
    if ctx is None or not is_allowed(ctx.message.chat_jid, ALLOWLIST):
        return {"error": "Message not found or not in the allowlist."}
    ctx.before = filter_messages(ctx.before, ALLOWLIST)
    ctx.after = filter_messages(ctx.after, ALLOWLIST)
    return ctx
```

`search_contacts` — return allowlisted contacts only:

```python
@mcp.tool()
def search_contacts(query: str):
    contacts = whatsapp_search_contacts(query)
    return filter_contacts(contacts, ALLOWLIST)
```

`download_media` — guard by the message's chat:

```python
@mcp.tool()
def download_media(message_id: str, chat_jid: str):
    if not is_allowed(chat_jid, ALLOWLIST):
        return {"error": f"{chat_jid} is not in the allowlist."}
    return whatsapp_download_media(message_id, chat_jid)
```

- [ ] **Step 5: Delete the three deferred convenience tools**

Remove the `@mcp.tool()` functions `get_direct_chat_by_contact`, `get_contact_chats`, and `get_last_interaction` entirely (function bodies and decorators). Leave their underlying `whatsapp.py` functions in place (unused, harmless).

- [ ] **Step 6: Add the `list_allowed_chats` tool**

```python
@mcp.tool()
def list_allowed_chats():
    """Return the chats and groups the agent is permitted to read and message."""
    return [{"jid": jid, "label": label} for jid, label in ALLOWLIST.items()]
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd whatsapp-mcp-server && uv run pytest tests/ -v`
Expected: PASS — Task 2-4 tests plus the 2 new read-tool tests.

- [ ] **Step 8: Commit**

```bash
git add whatsapp-mcp-server/main.py whatsapp-mcp-server/tests/test_tools_read.py
git commit -m "feat: scope read tools to allowlist; add list_allowed_chats; trim convenience tools"
```

---

### Task 6: Wire send guards into the send tools; remove `send_audio_message`

**Files:**
- Modify: `whatsapp-mcp-server/main.py`
- Test: `whatsapp-mcp-server/tests/test_tools_send.py`

**Interfaces:**
- Consumes: `check_send`, `AllowlistError` from Task 3; module-level `ALLOWLIST` from Task 5; upstream `whatsapp.send_message` / `whatsapp.send_file` (aliased `whatsapp_send_message`, `whatsapp_send_file`, returning `Tuple[bool, str]`).
- Produces: `send_message` and `send_file` that reject off-list recipients before calling the bridge; removal of the `send_audio_message` tool.

- [ ] **Step 1: Write the failing tests**

```python
# whatsapp-mcp-server/tests/test_tools_send.py
import importlib
import pytest


@pytest.fixture
def main_with_allowlist(tmp_path, monkeypatch):
    path = tmp_path / "allowed_chats.json"
    path.write_text('{"chats":[{"jid":"111@s.whatsapp.net","label":"Mom"}]}')
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(path))
    import main
    importlib.reload(main)
    return main


def test_send_to_allowed_recipient_calls_bridge(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    calls = []
    monkeypatch.setattr(main, "whatsapp_send_message",
                        lambda recipient, message: calls.append((recipient, message)) or (True, "sent"))
    result = main.send_message("111", "hi mom")
    assert calls == [("111@s.whatsapp.net", "hi mom")]
    assert result["success"] is True


def test_send_to_unlisted_recipient_is_blocked(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    calls = []
    monkeypatch.setattr(main, "whatsapp_send_message",
                        lambda recipient, message: calls.append(1) or (True, "sent"))
    result = main.send_message("999", "should not go")
    assert result["success"] is False
    assert calls == []  # bridge never called


def test_send_audio_message_removed(main_with_allowlist):
    assert not hasattr(main_with_allowlist, "send_audio_message")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd whatsapp-mcp-server && uv run pytest tests/test_tools_send.py -v`
Expected: FAIL — off-list send not blocked and/or `send_audio_message` still present.

- [ ] **Step 3: Replace the send tools**

```python
@mcp.tool()
def send_message(recipient: str, message: str):
    """Send a text message to an allowlisted person or group."""
    try:
        jid = check_send(recipient, ALLOWLIST)
    except AllowlistError as e:
        return {"success": False, "message": str(e)}
    success, status = whatsapp_send_message(jid, message)
    return {"success": success, "message": status}


@mcp.tool()
def send_file(recipient: str, media_path: str):
    """Send an image, video, or document to an allowlisted person or group."""
    try:
        jid = check_send(recipient, ALLOWLIST)
    except AllowlistError as e:
        return {"success": False, "message": str(e)}
    success, status = whatsapp_send_file(jid, media_path)
    return {"success": success, "message": status}
```

Ensure the imports near the top alias the bridge calls:
`from whatsapp import send_message as whatsapp_send_message, send_file as whatsapp_send_file`.

- [ ] **Step 4: Remove the `send_audio_message` tool**

Delete the `@mcp.tool()` `send_audio_message` function and its decorator. Remove any now-unused `audio` import if present.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd whatsapp-mcp-server && uv run pytest tests/ -v`
Expected: PASS — all tests including the 3 new send tests.

- [ ] **Step 6: Commit**

```bash
git add whatsapp-mcp-server/main.py whatsapp-mcp-server/tests/test_tools_send.py
git commit -m "feat: scope send tools to allowlist; remove audio tool"
```

---

### Task 7: `manage_allowlist.py` admin CLI

**Files:**
- Create: `manage_allowlist.py` (repo root)
- Test: `whatsapp-mcp-server/tests/test_manage_allowlist.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (standalone; reads the same `allowed_chats.json` shape).
- Produces:
  - `read_entries(path: str) -> list[dict]` — returns the `chats` list, or `[]` if the file does not exist.
  - `add_entry(path: str, jid: str, label: str) -> None` — appends `{jid, label}` (idempotent on `jid`), writing the `{"chats": [...]}` shape.
  - `remove_entry(path: str, jid: str) -> None` — drops the entry with that `jid`.
  - `search_db(db_path: str, query: str) -> list[dict]` — queries the full chats table (`SELECT jid, name FROM chats WHERE name LIKE ?`) and returns `[{"jid", "name"}]` for ALL chats (no allowlist filter — this is the out-of-band discovery path).
  - `main(argv)` — argparse dispatch for `search` / `add` / `remove` / `list`.

- [ ] **Step 1: Write the failing tests**

```python
# whatsapp-mcp-server/tests/test_manage_allowlist.py
import sqlite3
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import manage_allowlist as m


def test_add_then_read_roundtrips(tmp_path):
    path = str(tmp_path / "allowed_chats.json")
    m.add_entry(path, "111@s.whatsapp.net", "Mom")
    assert m.read_entries(path) == [{"jid": "111@s.whatsapp.net", "label": "Mom"}]


def test_add_is_idempotent_on_jid(tmp_path):
    path = str(tmp_path / "allowed_chats.json")
    m.add_entry(path, "111@s.whatsapp.net", "Mom")
    m.add_entry(path, "111@s.whatsapp.net", "Mom Updated")
    entries = m.read_entries(path)
    assert len(entries) == 1
    assert entries[0]["label"] == "Mom Updated"


def test_remove_entry(tmp_path):
    path = str(tmp_path / "allowed_chats.json")
    m.add_entry(path, "111@s.whatsapp.net", "Mom")
    m.add_entry(path, "222@g.us", "Family")
    m.remove_entry(path, "111@s.whatsapp.net")
    assert m.read_entries(path) == [{"jid": "222@g.us", "label": "Family"}]


def test_read_missing_file_returns_empty(tmp_path):
    assert m.read_entries(str(tmp_path / "nope.json")) == []


def test_search_db_returns_all_matches(tmp_path):
    db = str(tmp_path / "messages.db")
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE chats (jid TEXT, name TEXT)")
    conn.execute("INSERT INTO chats VALUES ('111@s.whatsapp.net','Mom')")
    conn.execute("INSERT INTO chats VALUES ('999@s.whatsapp.net','Mob Boss')")
    conn.commit()
    conn.close()
    results = m.search_db(db, "Mo")
    assert {r["jid"] for r in results} == {"111@s.whatsapp.net", "999@s.whatsapp.net"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd whatsapp-mcp-server && uv run pytest tests/test_manage_allowlist.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'manage_allowlist'`.

- [ ] **Step 3: Write `manage_allowlist.py`**

```python
#!/usr/bin/env python3
"""Admin CLI to curate allowed_chats.json. NOT exposed over MCP.

Searches the full WhatsApp chat database so the user can discover JIDs, then
adds/removes them from the allowlist the MCP server enforces.
"""
import argparse
import json
import os
import sqlite3

DEFAULT_ALLOWLIST = os.path.join(
    os.path.dirname(__file__), "whatsapp-mcp-server", "allowed_chats.json")
DEFAULT_DB = os.path.join(
    os.path.dirname(__file__), "whatsapp-bridge", "store", "messages.db")


def read_entries(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f).get("chats", [])


def _write_entries(path: str, entries: list) -> None:
    with open(path, "w") as f:
        json.dump({"chats": entries}, f, indent=2)


def add_entry(path: str, jid: str, label: str) -> None:
    entries = [e for e in read_entries(path) if e["jid"] != jid]
    entries.append({"jid": jid, "label": label})
    _write_entries(path, entries)


def remove_entry(path: str, jid: str) -> None:
    _write_entries(path, [e for e in read_entries(path) if e["jid"] != jid])


def search_db(db_path: str, query: str) -> list:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT jid, name FROM chats WHERE name LIKE ? ORDER BY name",
            (f"%{query}%",),
        ).fetchall()
    finally:
        conn.close()
    return [{"jid": jid, "name": name} for jid, name in rows]


def main(argv=None):
    p = argparse.ArgumentParser(description="Curate the WhatsApp MCP allowlist.")
    p.add_argument("--allowlist", default=DEFAULT_ALLOWLIST)
    p.add_argument("--db", default=DEFAULT_DB)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("query")
    a = sub.add_parser("add"); a.add_argument("jid"); a.add_argument("label")
    r = sub.add_parser("remove"); r.add_argument("jid")
    sub.add_parser("list")
    args = p.parse_args(argv)

    if args.cmd == "search":
        for row in search_db(args.db, args.query):
            print(f"{row['jid']}\t{row['name']}")
    elif args.cmd == "add":
        add_entry(args.allowlist, args.jid, args.label)
        print(f"Added {args.label} ({args.jid})")
    elif args.cmd == "remove":
        remove_entry(args.allowlist, args.jid)
        print(f"Removed {args.jid}")
    elif args.cmd == "list":
        for e in read_entries(args.allowlist):
            print(f"{e['jid']}\t{e.get('label','')}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd whatsapp-mcp-server && uv run pytest tests/test_manage_allowlist.py -v`
Expected: PASS — 5 passed.

- [ ] **Step 5: Commit**

```bash
git add manage_allowlist.py whatsapp-mcp-server/tests/test_manage_allowlist.py
git commit -m "feat: manage_allowlist.py admin CLI for JID discovery and curation"
```

---

### Task 8: Permission configuration and setup docs

**Files:**
- Create: `README.md` (repo root)
- Create: `.mcp.json.example` (repo root)

**Interfaces:**
- Consumes: everything above.
- Produces: documentation for QR auth, allowlist bootstrap, MCP registration, and the permission settings that make every send prompt for confirmation.

- [ ] **Step 1: Write `.mcp.json.example`**

This is the Claude Code MCP registration the user copies to `.mcp.json`. Read tools and `list_allowed_chats` are auto-approved; **send tools are deliberately omitted from `autoApprove` so each send raises a confirmation prompt** (the human gate from the design).

```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "uv",
      "args": ["--directory", "whatsapp-mcp-server", "run", "main.py"],
      "autoApprove": [
        "list_chats", "list_messages", "get_chat", "get_message_context",
        "search_contacts", "download_media", "list_allowed_chats"
      ]
    }
  }
}
```

- [ ] **Step 2: Write `README.md`**

````markdown
# WhatsApp MCP (personal, allowlist-scoped)

Read and send WhatsApp messages from Claude Code, restricted to an explicit
allowlist of people and groups. Every send requires your confirmation.

> **Warning:** This uses an unofficial WhatsApp connection, which violates
> WhatsApp's Terms of Service and can get your number banned. Use a personal
> account you accept that risk on, at low volume.

## Setup

1. **Start the bridge and scan the QR** (first run only; session lasts ~20 days):
   ```bash
   cd whatsapp-bridge && go run main.go
   ```
   Scan the QR with WhatsApp → Settings → Linked Devices. Leave it running.

2. **Curate the allowlist.** Find JIDs and add them (the server reads/sends
   nothing until you do — it is fail-closed):
   ```bash
   python manage_allowlist.py search "Mom"
   python manage_allowlist.py add 1234567890@s.whatsapp.net "Mom"
   python manage_allowlist.py list
   ```

3. **Register the MCP server:** copy `.mcp.json.example` to `.mcp.json`.
   Send tools are intentionally not auto-approved, so Claude Code prompts you to
   confirm every outgoing message.

## Tools

Read (allowlist-filtered): `list_chats`, `list_messages`, `get_chat`,
`get_message_context`, `search_contacts`, `download_media`, `list_allowed_chats`.
Send (allowlist-checked + confirmation): `send_message`, `send_file`.

## Tests

```bash
cd whatsapp-mcp-server && uv run pytest tests/ -v
```
````

- [ ] **Step 3: Verify the full test suite passes**

Run: `cd whatsapp-mcp-server && uv run pytest tests/ -v`
Expected: PASS — all tests from Tasks 2-7 green.

- [ ] **Step 4: Commit**

```bash
git add README.md .mcp.json.example
git commit -m "docs: setup, allowlist bootstrap, and send-confirmation permission config"
```

---

## Self-Review notes

- **Spec coverage:** allowlist scoping (Tasks 2,4,5), send check (Tasks 3,6), fail-closed (Task 2), confirmation via permission prompt (Task 8), tool trim + `list_allowed_chats` (Tasks 5,6), out-of-band `manage_allowlist.py` (Task 7), QR/setup docs (Task 8). All spec sections map to a task.
- **Bridge** is vendored unchanged (Task 1) per the design's "test our layer" decision.
- **Deferred items** (audio, three convenience getters) are explicitly removed in Tasks 5-6, matching the spec's "out of scope" list.
