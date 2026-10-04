# AgentNarna

AgentNarna is an OpenCode-powered security research workspace for authorized
pentests and bug bounty programs. It is not merely a collection of terminal
scripts: OpenCode is the primary interface, while the repository supplies the
specialized skills, commands, agents, memory, scanners, validation gates, and
reporting workflow behind it.

> Use AgentNarna only on assets and techniques explicitly authorized by the
> engagement or bug bounty program. Reports remain subject to human review.

## Launch the full platform

Requirements: Linux, Git, Bash, Python 3.10+, and
[OpenCode](https://opencode.ai).

```bash
git clone https://github.com/narna00/agentnarna.git
cd agentnarna

# Recommended: install the external recon/scanning tools.
chmod +x install_tools.sh install.sh
./install_tools.sh

# Install all AgentNarna skills, commands, and agents into this workspace.
./install.sh --agent opencode --project

# This is the main AgentNarna experience.
opencode
```

Inside OpenCode, speak naturally:

```text
recon target.example
hunt target.example
run autopilot on target.example in normal mode
test the authorization boundary with user A and user B
validate this finding
write a submission-ready report
```

OpenCode reads `AGENTS.md` from the repository and discovers the installed
`.opencode/skills`, `.opencode/commands`, and `.opencode/agents` directories.
The installer copies the complete workspace; it does not replace it with a
smaller command-line interface.

## What is included

The OpenCode workspace currently contains:

- **40+ hunting commands** covering recon, exploitation, validation, reporting,
  scope, memory, cloud, mobile, Web3, LLM applications, source review, and PoCs.
- **21 specialized skills** with routing for vulnerability classes, platforms,
  controls, and target technologies.
- **10 cooperating agents** for recon ranking, autonomous hunting, credentials,
  validation, exploit chains, Web3, tokens, and report writing.
- **70+ local tools** and integrations for recon, scanning, verification,
  evidence management, Burp, Caido, HackerOne, and MCP clients.
- Persistent hunt memory, resumable sessions, audit logs, scope enforcement,
  adaptive validation, and verified-only report generation.

External tools are helpers. OpenCode coordinates the workflow, selects the
relevant skill or agent, interprets results, changes strategy, and maintains
the investigation state.

## Main workflow

```text
OpenCode
   ↓
scope → recon → attack-surface ranking → focused hunt
   ↓                                      ↓
memory ← control fingerprint ← adaptive validation
   ↓                                      ↓
suppressed candidate              deterministic proof
                                          ↓
                              verified finding → report
```

### Recon and attack-surface analysis

```text
recon target.example
surface target.example
intel target.example
scope-aggregate program-name
```

### Focused and autonomous hunting

```text
hunt target.example
run autopilot on target.example in normal mode
pick up the previous hunt for target.example
test this GraphQL workflow for cross-tenant authorization failures
audit this LLM application for tool and data boundary failures
```

### Validation and reporting

```text
validate this finding
verify the claimed impact with a fresh session
build an exploit chain from the verified findings
write a HackerOne report using only linked evidence
```

## Commands

OpenCode invokes these from natural-language requests. The command documents
remain available under `commands/` for transparent review.

| Area | Commands |
|---|---|
| Core workflow | `recon`, `hunt`, `autopilot`, `surface`, `pickup`, `remember` |
| Proof and reporting | `validate`, `verify`, `triage`, `chain`, `poc`, `report`, `screenshot` |
| Scope and intelligence | `scope`, `scope-aggregate`, `intel`, `breach-check`, `osint-employees` |
| Web/API testing | `bypass-403`, `cors`, `crlf`, `domxss`, `jwt-scan`, `nosqli`, `oob`, `param-discover`, `spray` |
| Recon and exposure | `scan-cves`, `secrets-hunt`, `takeover`, `wordlist-gen`, `portscan`, `cloud-recon` |
| Source and infrastructure | `sast`, `cicd-security` through skills, `arsenal`, `memory-gc`, `dashboard` |
| AI and agentic systems | `llm-app-audit`, `llm-redteam` |
| Web3 | `web3-audit`, `token-scan` |

## Skills

| Skill | Purpose |
|---|---|
| `bug-bounty` | Master workflow and task routing |
| `bb-methodology` | Non-linear human-style hunting methodology |
| `adaptive-exploit-validation` | Learn from controls and change strategy families |
| `triage-validation` | Seven-question gate and deterministic proof boundary |
| `report-writing` | Submission-ready, evidence-bound reports |
| `research-intelligence` | Medium, X, RSS, disclosure, and advisory technique cards |
| `web2-recon` | Asset discovery and attack-surface mapping |
| `web2-vuln-classes` | Web/API vulnerability classes and control-aware testing |
| `graphql-audit` | GraphQL schema, resolver, auth, and batching risks |
| `cloud-pentest` | AWS, Azure, GCP, storage, identity, and metadata surfaces |
| `mobile-pentest` | Android/iOS static and dynamic review |
| `client-reverse` | Client, bundle, protocol, and desktop reverse engineering |
| `cicd-security` | Pipeline, runner, artifact, and secret boundary review |
| `credential-attack` | Authorized authentication and credential workflow assessment |
| `agentic-app-audit` | Tool-use, memory, prompt, and agent authorization boundaries |
| `llm-redteam` | LLM application and model integration testing |
| `mcp-server-audit` | MCP tools, transports, authorization, and confused-deputy review |
| `security-arsenal` | Payload/tool routing and technique references |
| `argus` | Recon and investigation support |
| `web3-audit` | Smart-contract and DeFi testing |
| `meme-coin-audit` | Token authority, liquidity, and rug-pull analysis |

## What AgentNarna improves

### Adaptive validation

A 403, WAF page, sanitizer, CSP, or rate limit is treated as a control
fingerprint. The investigation records attempted strategy families and requires
the next attempt to test a different assumption—identity, route, parser,
encoding stage, workflow state, or first-party surface—instead of blindly
mutating the same payload.

The agent stops when meaningful, in-scope strategy families are exhausted. It
does not pretend every target must contain a vulnerability.

### Verified-only findings

Scanner output is a lead, not a finding. Each reportable item must have its own
`validation.json`, a confirmed deterministic verifier result, and evidence
linked specifically to that validation record. Evidence from one verified issue
cannot promote unrelated scanner output.

```text
lead → candidate → verified finding → reportable → human submission
          └──────── rejected/suppressed when proof fails
```

### Compact research intelligence

Medium tags and publications use public RSS/Atom and require no account:

```bash
agentnarna research --medium-tag web-security --medium-tag bug-bounty
```

X recent search uses the official API:

```bash
export X_BEARER_TOKEN="..."
agentnarna research --x-query '(bug bounty OR pentest) (bypass OR writeup) -is:retweet'
```

OpenCode can then use the local research ledger during a hunt. At most three
relevance-ranked cards and 1,800 characters enter an exploit prompt. Posts are
untrusted hypotheses and never count as proof.

### Minimal token waste

Minimal artifact mode is the default. It retains actionable state, evidence,
and final report candidates without saving rejected report drafts or verbose
model transcripts.

```bash
export AGENTNARNA_ARTIFACT_MODE=minimal
```

Use `audit` only when the complete investigation trail is required.

## Operator dashboard

The local dashboard is an additional view of hunt state; it is not a
replacement for OpenCode.

```bash
python3 bughunter/tools/hunt_dashboard.py serve --port 8777
```

It shows attack-surface state, leads, active investigations, verified findings,
suppressed candidates, and report artifacts.

## Optional standalone CLI

Standalone mode is retained for automation, CI, and users who do not want an
agent harness. It is **not** the primary OpenCode interface.

```bash
./install.sh --agent standalone
agentnarna setup
agentnarna hunt target.example
```

The legacy `bughunter` command remains a compatibility alias.

## Other supported harnesses

```bash
./install.sh                         # Claude Code global integration
./install.sh --agent opencode        # OpenCode global integration
./install.sh --agent codex --project # project-local Codex skills
./install.sh --agent pi --project    # project-local Pi integration
./install.sh --agent all             # every global target
```

See `OPENCODE.md`, `CLAUDE.md`, and `docs/` for integration details.

## Testing

```bash
python3 -m pip install -e '.[test]'
python3 -m pytest -q
```

GitHub Actions tests Python 3.10–3.12 and performs an Ubuntu clone/install
smoke test.

## Attribution

AgentNarna is based on the MIT-licensed
[AwareXone Agentic Bug Hunter](https://github.com/Awarexone/Agentic-Bug-Hunter).
The upstream license and copyright notice remain in `LICENSE`.
