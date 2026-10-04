# agentnarna

Evidence-first agentic security research for authorized pentests and bug bounty
programs.

agentnarna separates attack-surface observations from actual findings. A lead is
promoted only after a deterministic verifier reproduces real impact, and the
report writer can see only the evidence linked to that exact validation record.

> Use only on assets and techniques explicitly authorized by the engagement or
> program policy. The tool does not submit reports automatically.

## Why this fork exists

Many automated hunting flows overproduce artifacts, stop at controls, and let
scanner confidence turn into report language. agentnarna changes the operating
model:

- **Adaptive validation:** 403/WAF/sanitizer/CSP/rate-limit responses are
  fingerprinted and used to choose a different strategy family.
- **Verified-only reporting:** one verified issue cannot promote unrelated
  scanner output from the same directory.
- **Minimal persistence by default:** rejected drafts, `NO_REPORTS`, and verbose
  model workings are not saved unless audit mode is enabled.
- **Source-linked learning:** Medium, X, RSS, HackerOne, and advisory material
  becomes hypothesis-only intel—not executable instructions or proof.
- **A visible proof spine:** the local dashboard distinguishes leads,
  investigating candidates, verified findings, suppressed candidates, and final
  submission artifacts.

No automated system can guarantee a bounty or replace the judgment of a skilled
manual tester. Reliability here means a stricter false-positive boundary,
measurable verification, and better continuity between attempts.

## Proof model

```text
lead -> candidate -> verified finding -> reportable -> human submission
          |                 |
          |                 +-- fresh deterministic oracle + linked evidence
          +-- never appears in a report on scanner confidence alone
```

Every reportable item needs its own `validation.json` with
`status=validated_finding` and a confirmed verifier result. Evidence files must
be explicitly linked from that validation record and remain inside the finding
directory.

## Install from GitHub on Linux

Python 3.10+, Git, and Bash are required. Replace `YOUR_USERNAME` after this
repository is published under your GitHub account.

```bash
git clone https://github.com/YOUR_USERNAME/agentnarna.git
cd agentnarna
chmod +x install.sh uninstall.sh
./install.sh --agent standalone
agentnarna setup
```

The installer creates `agentnarna` in `/usr/local/bin` when writable, otherwise
in `~/.local/bin`. It also creates `bughunter` as a migration alias. Rerun the
same installer after `git pull` to update both links.

For an isolated Python environment instead:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
agentnarna --help
```

Uninstall the global launchers without deleting saved configuration:

```bash
./uninstall.sh --agent standalone --yes
```

External recon tools are optional and discovered at runtime. See
[`install_tools.sh`](install_tools.sh) and
[`bughunter/tools/README.md`](bughunter/tools/README.md).

## Core commands

```bash
agentnarna recon target.example
agentnarna hunt target.example
agentnarna validate "candidate description"
agentnarna report --findings-dir findings/target.example
agentnarna status
```

Run the local operator dashboard:

```bash
python3 bughunter/tools/hunt_dashboard.py serve --port 8777
```

The dashboard binds to loopback by default and includes Host-header protection.

## Research intelligence

Medium uses public RSS/Atom and needs no credentials:

```bash
agentnarna research \
  --medium-tag web-security \
  --medium-tag bug-bounty
```

X recent search uses the official API and a bearer token from your X developer
project:

```bash
export X_BEARER_TOKEN="..."
agentnarna research \
  --x-query '(bug bounty OR pentest) (bypass OR writeup) -is:retweet'
```

Other feeds and articles can be ingested explicitly:

```bash
agentnarna research --feed https://example.org/security/feed.xml
agentnarna research --url https://example.org/research/article
```

The default ledger is `$AGENTNARNA_HOME/hunt-memory/technique-intel.jsonl`
(the repository root for a source checkout). The exploit loop automatically
loads at most three relevance-ranked cards and caps them at 1,800 characters,
so research does not consume the whole model context. Entries are
deduplicated, attributed, treated as untrusted external content, and labeled
`hypothesis_only_requires_live_verification`.

## Adaptive validation

The exploit loop classifies the latest response, remembers attempted strategy
families, and recommends a genuinely different next direction. Examples:

- 403/WAF: path normalization, safe method semantics, proxy routing, or an
  alternate first-party implementation.
- XSS/sanitization: map output context, decoding stages, alternate sinks, CSP
  boundaries, and confirm only with a browser execution oracle.
- Authorization: compare anonymous, controlled identity A, and controlled
  identity B; status differences alone are not impact.
- Rate controls: identify the legitimate keying boundary without causing load.

Generated commands still require operator confirmation before execution. This
keeps the agent inside the current scope and prevents target-controlled text
from silently turning into shell execution.

## Artifact modes

Minimal is the default:

```bash
export AGENTNARNA_ARTIFACT_MODE=minimal
```

It retains compact actionable state, linked proof, and final report candidates.
For a full gate/exploit reasoning trail:

```bash
export AGENTNARNA_ARTIFACT_MODE=audit
```

`BBHUNT_ARTIFACT_MODE`, `BUGHUNTER_HOME`, and the old CLI names remain migration
aliases. New data/config locations are controlled with `AGENTNARNA_HOME` and
`~/.agentnarna/config.json`.

## Skills

The existing domain skills remain available. Two cross-cutting skills define
the new behavior:

- [`adaptive-exploit-validation`](skills/adaptive-exploit-validation/SKILL.md)
- [`research-intelligence`](skills/research-intelligence/SKILL.md)

The master methodology, validation, and reporting skills route through those
contracts. Run the bundled skill validator when changing a skill:

```bash
python <skill-creator>/scripts/quick_validate.py skills/adaptive-exploit-validation
```

## Tests

```bash
python -m pip install -e '.[test]'
python -m pytest -q
```

The suite includes false-positive fixtures, deterministic verifier benchmarks,
evidence provenance, scope enforcement, prompt-injection delimiting, report
gating, shell confirmation, and dashboard safety.

## Project layout

```text
bughunter/engine.py                 CLI and provider dispatch
bughunter/brain.py                  reasoning, adaptive exploit loop, report gate
bughunter/tools/adaptive_strategy.py response fingerprint and strategy routing
bughunter/tools/report_evidence.py  per-finding verified evidence binding
bughunter/tools/technique_intel.py  Medium/X/RSS/article ingestion
bughunter/tools/verifiers/          deterministic vulnerability oracles
skills/                             agent skills and methodology
site/index.html                     agentnarna product UI
tests/                              regression and verifier benchmark suite
```

## Attribution

agentnarna is based on the MIT-licensed
[AwareXone Agentic Bug Hunter](https://github.com/Awarexone/Agentic-Bug-Hunter).
The upstream license and copyright notice are preserved in [`LICENSE`](LICENSE).
