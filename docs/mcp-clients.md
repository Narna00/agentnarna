# MCP Clients

Primary transport: **stdio** (dual-era MCP SDK v2).

| Host | Config |
|---|---|
| Claude Code | Merge `bughunter/mcp/bughunter-mcp/claude-config.json` into `mcpServers` |
| OpenCode | Merge `bughunter/mcp/bughunter-mcp/opencode-config.json` |
| Cursor | Point `command`/`args` at `python3 bughunter/mcp/bughunter-mcp/server.py` |
| Codex | Same stdio command pattern |

Run from the repo root so relative paths resolve.

```bash
agentnarna mcp doctor
```

Do not enable `AGENTNARNA_MCP_APPROVE=1` in shared configs by default.
