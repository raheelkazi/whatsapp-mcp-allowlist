# Contributing

Thanks for your interest in improving this project! It's a small, allowlist-scoped
WhatsApp MCP server. Contributions of all sizes are welcome — bug fixes,
documentation, and well-scoped features.

## Ground rules

- **Security first.** The whole point of this fork is the allowlist permission layer.
  Any change to `whatsapp-mcp-server/allowlist.py` or the tool guards in `main.py`
  must keep the invariants intact: reads are scoped to the allowlist, sends are
  rejected for off-list recipients *before* hitting the bridge, and the server
  fails closed when the allowlist is missing/malformed. Add tests proving it.
- **Never commit personal data.** `whatsapp-bridge/store/`, `allowed_chats.json`, and
  `.mcp.json` are gitignored — keep it that way. Don't put real phone numbers, JIDs,
  or contact names in tests or docs; use placeholders like `111@s.whatsapp.net`.
- **Respect the ToS reality.** This uses an unofficial connection. Don't add features
  designed for bulk/automated high-frequency messaging — that gets users banned and
  isn't the goal of this project.

## Development setup

```bash
# Python MCP server
cd whatsapp-mcp-server
uv sync
uv run pytest tests/ -v

# Go bridge
cd ../whatsapp-bridge
go build -o /dev/null .
```

## Making a change

1. Fork and create a branch (`git checkout -b fix/short-description`).
2. Write a failing test first when fixing a bug or adding behavior (see the existing
   tests in `whatsapp-mcp-server/tests/` for the patterns — the `main_with_allowlist`
   fixture in `conftest.py` reloads the server against a temp allowlist).
3. Keep changes focused; match the surrounding style.
4. Run the full suite (`uv run pytest tests/ -v`) and make sure the Go bridge still
   builds.
5. Open a PR. CI runs the Python suite and the Go build on every PR.

## Reporting bugs / requesting features

Use the issue templates. For bugs, include what you expected, what happened, and the
minimal steps to reproduce — **with no personal data** (redact real numbers/names).

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
