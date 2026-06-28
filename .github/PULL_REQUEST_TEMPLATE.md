## What & why

Briefly describe the change and the motivation.

## Checklist

- [ ] Tests added/updated and `uv run pytest tests/ -v` passes
- [ ] Go bridge still builds (`go build -o /dev/null .` in `whatsapp-bridge/`)
- [ ] No personal data committed (real numbers/JIDs/names) — placeholders only
- [ ] Allowlist guarantees preserved: scoped reads, off-list sends rejected before the
      bridge, fail-closed on missing/malformed allowlist
- [ ] Focused change; matches surrounding style
