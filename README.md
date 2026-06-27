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
   python3 manage_allowlist.py search "Mom"
   python3 manage_allowlist.py add 1234567890@s.whatsapp.net "Mom"
   python3 manage_allowlist.py list
   ```

3. **Register the MCP server.** Copy `.mcp.json.example` to `.mcp.json` in the
   project root — this tells Claude Code how to launch the server:
   ```bash
   cp .mcp.json.example .mcp.json
   ```
   Then copy `.claude/settings.json` into your project's `.claude/` directory to
   auto-approve the 7 read-only tools so Claude Code can call them without
   prompting:
   ```bash
   cp .claude/settings.json .claude/settings.json
   ```
   The `permissions.allow` entries follow the Claude Code naming convention
   `mcp__<server>__<tool>`. The send tools (`send_message`, `send_file`) are
   deliberately omitted from the allow-list, so every outgoing message requires
   your explicit confirmation before it is sent.

## Tools

Read (allowlist-filtered): `list_chats`, `list_messages`, `get_chat`,
`get_message_context`, `search_contacts`, `download_media`, `list_allowed_chats`.
Send (allowlist-checked + confirmation): `send_message`, `send_file`.

## Tests

```bash
cd whatsapp-mcp-server && uv run pytest tests/ -v
```
