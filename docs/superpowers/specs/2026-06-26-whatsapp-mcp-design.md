# WhatsApp MCP Server — Design

**Date:** 2026-06-26
**Status:** Approved, ready for planning

## Goal

A WhatsApp MCP server that lets Claude Code agents **read and send** messages on the
user's **personal** WhatsApp account, but only for an explicitly curated set of
**specific people and groups**. Every send additionally requires live human
confirmation.

## Context & constraints

- **No official personal-account API.** WhatsApp's official Business/Cloud API is for
  business accounts only. Personal-account access requires unofficial routes
  (reverse-engineered protocol or WhatsApp Web automation), which **violate WhatsApp's
  Terms of Service** and carry a real risk of the number being temporarily or
  permanently banned. The user accepts this trade for low-volume personal use.
- **Deployment:** local, on-demand. Runs as an MCP server (stdio) that Claude Code
  spawns during interactive sessions. The WhatsApp session persists to disk between
  runs. No always-on daemon, no cloud. The agent only acts while the user is in a
  Claude session.

## Approach

Fork **lharries/whatsapp-mcp** (Approach A) as the foundation:

- **Go `whatsmeow` bridge** — speaks the WhatsApp multi-device WebSocket protocol,
  handles QR authentication, stores messages/chats in local SQLite. Forked ~as-is.
- **Python MCP server (FastMCP)** — exposes tools to Claude. This is where we add the
  new work.

The novel work is a **scoping / permission layer** in the Python MCP server. Upstream
exposes every chat with no restrictions; we add an allowlist guard.

## Architecture

```
Claude Code (user)
   │  MCP stdio
   ▼
Python MCP server (FastMCP)  ◄── tools, each wrapped by an ALLOWLIST GUARD
   │  local HTTP
   ▼
Go whatsmeow bridge  ──►  WhatsApp multi-device (WebSocket)
   │
   ▼
SQLite (messages.db, whatsapp.db) in whatsapp-bridge/store/
```

## Scoping model (defense-in-depth)

1. **`allowed_chats.json`** — user-curated. Each entry is a WhatsApp JID
   (`…@s.whatsapp.net` for people, `…@g.us` for groups) plus a human label.
2. **Read guard** — every read tool post-filters results to allowlisted JIDs only. A
   non-allowlisted chat does not exist from the agent's perspective; other
   conversations never enter agent context.
3. **Send guard** — every send tool rejects a target JID not on the allowlist *before*
   reaching the bridge. Off-list send → hard error, never silently delivered.
4. **Send confirmation** — layered via Claude Code's native permission prompt. Send
   tools are not auto-approved, so each send surfaces a confirm/deny prompt to the
   user. No custom confirmation code; documented as a permission setting.
5. **Fail-closed** — missing/malformed allowlist → server refuses to start. No
   allowlist means nothing is allowed, never everything.

## Tool surface (v1 ≈ 8 tools)

**Read tools (allowlist read-guard):**
- `list_chats` — filtered to allowlist.
- `list_messages` — rejects non-allowlisted `chat_jid`; unfiltered listing returns
  allowlisted only.
- `get_chat` — guarded.
- `get_message_context` — guarded.
- `search_contacts` — returns allowlisted contacts only (agent cannot enumerate the
  full address book).
- `download_media` — guarded by the referenced message's chat JID.

**Send tools (allowlist send-guard + permission prompt):**
- `send_message` — send text. Core.
- `send_file` — send image/video/document.

**Admin/visibility:**
- `list_allowed_chats` — returns the current allowlist (labels + JIDs). Read-only, no
  guard.

**Deferred (explicitly out of v1):**
- `send_audio_message` — niche, adds FFmpeg dependency.
- `get_direct_chat_by_contact`, `get_contact_chats`, `get_last_interaction` — thin
  conveniences the agent can compose from `list_chats` / `list_messages`. Re-add later
  if missed.

## Allowlist management (out of band)

The unscoped "see everything" capability stays with the user, off the agent's tool
surface:

- **`manage_allowlist.py`** — a CLI the user runs directly (not an MCP tool):
  - `search "<name>"` — queries the *full* SQLite contact/chat tables, shows matches
    with JIDs.
  - `add <jid> "<label>"` — appends to `allowed_chats.json`.
  - `list` / `remove <jid>` — manage entries.

This solves the bootstrapping problem: `search_contacts` over MCP is allowlist-limited,
so the user uses the CLI to discover JIDs and populate the list.

## Error handling

- **Off-list send target** → clear error (`"<jid> is not in the allowlist; add it with
  manage_allowlist.py"`), never falls through to the bridge.
- **Bridge down / session expired** → structured "bridge unavailable, re-scan QR"
  message; tools do not hang.
- **Allowlist missing/malformed** → fail-closed, server refuses to start.

## Testing

- **Guard unit tests (primary focus):** table-driven tests proving allowlisted JIDs
  pass and non-allowlisted JIDs are filtered (reads) / rejected (sends), for both read
  and send paths. Fail-closed on empty/missing allowlist is a test case.
- **Bridge:** the WhatsApp protocol layer is inherited and requires a live session +
  QR; tested manually, not unit-tested. We test *our* layer.

## Project structure

```
whatsapp-mcp/
├── whatsapp-bridge/          # Go (forked ~as-is)
│   └── main.go, store/
├── whatsapp-mcp-server/      # Python MCP
│   ├── main.py               # FastMCP server + tool defs
│   ├── allowlist.py          # the guard: load, read-filter, send-check
│   ├── allowed_chats.json    # user-curated list (gitignored)
│   └── tests/test_allowlist.py
├── manage_allowlist.py       # admin CLI (not an MCP tool)
└── docs/superpowers/specs/   # this design doc
```

## Dependencies

Go, Python 3.6+, `uv`. FFmpeg deferred with audio. A live WhatsApp account for QR auth.

## Out of scope (v1)

Always-on/proactive monitoring, remote hosting, audio messages, category-based
allowlists ("all work groups"), auto-send for trusted chats.
