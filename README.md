# WhatsApp MCP — allowlist-scoped

Let Claude (or any MCP client) **read and send WhatsApp messages on your personal
account — but only for an explicit allowlist of people and groups you choose.**
Everything else stays invisible, and every outgoing message requires your
confirmation.

> ⚠️ **Warning — read this first.** This uses an *unofficial* WhatsApp connection
> (via the reverse-engineered [whatsmeow](https://github.com/tulir/whatsmeow)
> protocol library). It **violates WhatsApp's Terms of Service and can get your
> number banned.** Use a personal account whose risk you accept, and keep volume
> low. Do **not** use it for bulk or automated high-frequency messaging — that is
> the fastest way to get banned.

## Why this fork exists

This is a fork of [**lharries/whatsapp-mcp**](https://github.com/lharries/whatsapp-mcp)
(MIT). The upstream exposes your *entire* WhatsApp — every chat is readable and any
number is messageable. This fork adds a **permission layer** so an agent only ever
touches what you've explicitly allowed:

- **Allowlist scoping (`allowed_chats.json`).** Read tools return results *only* for
  allowlisted chats; `search_contacts` can't enumerate your whole address book.
- **Send guard + confirmation.** Send tools reject any recipient not on the allowlist
  *before* hitting the network, and the two send tools are deliberately left out of
  auto-approval so your MCP client prompts you before every message goes out.
- **Fail-closed.** A missing or malformed allowlist makes the server refuse to start —
  it never defaults to "allow everything".
- **Out-of-band curation.** A standalone `manage_allowlist.py` CLI (not exposed as an
  MCP tool) lets *you* search your full contacts/chats to discover JIDs and edit the
  allowlist — that "see everything" power never reaches the agent.
- **Current `whatsmeow`.** Bumped from the stale upstream pin (which WhatsApp now
  rejects with `client outdated (405)`) to a current release.

## Architecture

```
MCP client (e.g. Claude Code)
   │  MCP stdio
   ▼
Python FastMCP server  ◄── every tool wrapped by the allowlist guard
   │  local HTTP
   ▼
Go whatsmeow bridge  ──►  WhatsApp (multi-device WebSocket)
   │
   ▼
SQLite (messages.db, whatsapp.db)  — local only, gitignored
```

## Setup

**Requirements:** Go, Python 3.6+, [`uv`](https://github.com/astral-sh/uv), and a
WhatsApp account to link.

1. **Start the bridge and scan the QR** (first run only; session lasts ~20 days):
   ```bash
   cd whatsapp-bridge && go run main.go
   ```
   Scan the QR with WhatsApp → Settings → Linked Devices. Leave it running.

2. **Curate the allowlist.** The server reads/sends nothing until you add entries
   (fail-closed). Use `--read-only` to allow reading a chat but never sending to it:
   ```bash
   python3 manage_allowlist.py search "Mom"          # find a JID by name
   python3 manage_allowlist.py add 1234567890@s.whatsapp.net "Mom"
   python3 manage_allowlist.py add 99999@g.us "Work Group" --read-only
   python3 manage_allowlist.py list                  # shows jid, label, mode
   ```

3. **Register the MCP server.** Copy the example launch config:
   ```bash
   cp .mcp.json.example .mcp.json
   ```
   The committed `.claude/settings.json` auto-approves the 7 read-only tools.
   The send tools (`send_message`, `send_file`) are intentionally omitted, so every
   outgoing message requires your explicit confirmation. (Entries follow the Claude
   Code convention `mcp__<server>__<tool>`; merge into your existing settings rather
   than overwriting.)

## Tools

- **Read (allowlist-filtered):** `list_chats`, `list_messages`, `get_chat`,
  `get_message_context`, `search_contacts`, `download_media`, `list_allowed_chats`
- **Send (allowlist-checked + confirmation):** `send_message`, `send_file`

## Safety controls

Beyond the allowlist, several guardrails reduce the blast radius and ban risk:

| Control | How |
|---|---|
| **Per-chat mode** | Each allowlist entry is `read` or `read+send` (default `read+send`; `--read-only` sets `read`). A `read` chat can be read but never messaged. |
| **Kill-switch** | `WHATSAPP_READ_ONLY=1` disables *all* sends at startup; reads still work. |
| **Send rate limit** | Sends are rejected (not queued) if they come faster than `WHATSAPP_SEND_MIN_INTERVAL_SEC` (default 3) apart or exceed `WHATSAPP_SEND_MAX_PER_HOUR` (default 30). Guards against accidental spam / bans. |
| **Audit log** | Every tool call (reads, sends, blocks) is appended as one JSON line to `WHATSAPP_AUDIT_LOG` (default `whatsapp-mcp-server/audit.log`, gitignored). |
| **Confirmation on send** | Send tools are omitted from auto-approval, so your MCP client prompts before each outgoing message. |

Reads also resolve group senders' `@lid` numeric IDs to real contact names.

## Privacy

Your synced messages (`whatsapp-bridge/store/`), your `allowed_chats.json`, your
local `.mcp.json`, and the `audit.log` are **gitignored** — they never leave your
machine.

## Tests

```bash
cd whatsapp-mcp-server && uv run pytest tests/ -v
```

## Credits & license

Forked from [lharries/whatsapp-mcp](https://github.com/lharries/whatsapp-mcp)
(© 2025 Luke Harries, MIT). Built on [whatsmeow](https://github.com/tulir/whatsmeow).
This project is released under the [MIT License](LICENSE); the upstream copyright is
retained therein.
