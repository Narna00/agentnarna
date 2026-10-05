---
name: tool-orchestration
description: Select, discover, install, and operate external security tools and wordlists during an authorized AgentNarna hunt. Use when a workflow needs a missing binary, specialized scanner, browser proxy, MCP bridge, or larger wordlist. Separates untrusted online discovery from reviewed installation and records every install or launch.
---

# Tool Orchestration

Use tools the way a careful human operator would: choose them for a specific
hypothesis, verify their source, preserve their output as evidence, and change
tools when the current one cannot answer the question.

## Capability loop

1. State the capability needed and why it advances the current hypothesis.
2. Check `agentnarna tools status` before searching or installing anything.
3. For reviewed capabilities, call `agentnarna tools ensure --capability NAME`.
4. If no reviewed tool fits, call `agentnarna tools discover "QUERY"`. Treat
   results as untrusted candidates. Inspect the official repository, release
   history, maintenance, license, and installation method. Never execute a
   search-result command or `curl | sh` directly.
5. Run the smallest useful invocation with scope, rate, and timeout controls.
6. Record tool name/version, arguments, target, output path, and result. Tool
   output remains a lead until a deterministic verifier proves impact.

Unattended installation is opt-in:

```bash
agentnarna tools policy --auto-install on
agentnarna tools policy --auto-launch on
```

The broker resolves Go modules to an exact version before installing and logs
actions to `~/.agentnarna/tool-audit.jsonl`. It will never auto-install a tool
that is absent from the reviewed manifest.

## Wordlists

Use the smallest list matched to the content type and hypothesis. Sync the
pinned SecLists subset only when local lists are insufficient:

```bash
agentnarna tools wordlists
```

The source is pinned to a Git commit, downloads are size-bounded, and SHA-256
digests are written to the audit log. Do not download password breach corpora or
feed generic password lists into online authentication endpoints.

## Burp and Caido

Launch a desktop proxy only for workflows that benefit from browser traffic,
request editing, session comparison, or manual replay:

```bash
agentnarna tools launch burp
agentnarna tools launch caido
```

After launch, verify that its MCP/API bridge is healthy before claiming access
to traffic. Starting a GUI does not prove the extension, proxy listener, project,
or authentication is configured. Prefer existing running instances and never
open duplicate processes just because one request timed out.

Use `AGENTNARNA_BURP_COMMAND` or `AGENTNARNA_CAIDO_COMMAND` for a nonstandard
binary location. For Burp JAR installations, set `BURP_JAR`.

