---
description: Select and prepare tools, wordlists, or Burp/Caido for the current authorized testing hypothesis.
---

# Tool orchestration

For `$ARGUMENTS`, load the `tool-orchestration` skill and:

1. Identify the concrete capability required by the current hypothesis.
2. Check the AgentNarna tool broker status.
3. Reuse an installed tool when suitable.
4. Otherwise ensure a reviewed capability under the operator's install policy.
5. Search online only when the reviewed manifest has no match; do not execute
   commands copied from results.
6. Launch Burp or Caido only when interactive proxying is useful, then verify
   the bridge/listener before using it.
7. Keep scanner output as a lead until target-specific verification succeeds.

Useful broker commands:

```bash
agentnarna tools status
agentnarna tools ensure --capability recon
agentnarna tools wordlists
agentnarna tools launch burp
agentnarna tools discover "graphql security scanner"
```

