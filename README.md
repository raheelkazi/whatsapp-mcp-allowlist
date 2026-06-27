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
