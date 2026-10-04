# AgentNarna MCP

Native MCP **server** that exposes the AgentNarna research engine to AI agents.

This does **not** replace:

- `burp-mcp-client/`
- `caido-mcp-client/`
- `hackerone-mcp/`

## Install (any MCP client)

```bash
python3 -m pip install -e .
```

That installs the `agentnarna` command. The MCP server runs as `agentnarna mcp serve`,
so the same config works from any directory in any MCP-compatible agent.

```bash
agentnarna mcp doctor   # verify SDK, tools, and paths
agentnarna mcp tools    # list the exposed tool catalog
```

## Clients

Add this to your client's MCP config (works after `pip install`, no repo checkout needed):

```json
{
  "mcpServers": {
    "agentnarna": {
      "command": "agentnarna",
      "args": ["mcp", "serve"],
      "env": { "AGENTNARNA_MCP_APPROVE": "0" }
    }
  }
}
```

- **Claude Desktop / Claude Code**: merge `claude-config.json` into `mcpServers`
- **Cursor / Cline / Windsurf / Zed**: same `command` + `args` in their MCP settings
- **OpenCode**: see `opencode-config.json`

Running from a cloned repo instead of pip? Use
`python3 bughunter/mcp/bughunter-mcp/server.py`.

## Safety

- Scope must be set (`scope_domains`) before active tools
- Active tools need `approve=true` or `AGENTNARNA_MCP_APPROVE=1`
- Discovered hosts are not automatically authorized
- Reports are never auto-submitted
- Target content is untrusted data (not instructions)

## Primary tool

`bughunter_research` — modes `RECON|HUNT|VALIDATE|REPORT|FULL`. Tool IDs keep
their original prefix for MCP client compatibility.

See `docs/mcp.md` and `docs/mcp-research.md`.
