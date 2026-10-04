# AgentNarna FAQ

## What is AgentNarna?

AgentNarna is an evidence-first assistant for authorized pentests and bug-bounty
work. It combines recon, hypothesis generation, adaptive validation,
deterministic verifiers, local memory, and verified-only report generation.

## Does it guarantee findings or bounty payments?

No. No automated system can guarantee that a target is vulnerable, that a
program will accept a report, or that a bounty will be paid. AgentNarna improves
coverage and false-positive control; it does not replace researcher judgment.

## What operating systems are supported?

Linux is the primary clone-and-run environment. macOS is supported by the same
Bash installer. The Python CLI and core test suite also run on Windows, while
the external reconnaissance arsenal is easiest to operate in Linux or WSL.

## How do I install it from GitHub on Linux?

```bash
git clone https://github.com/YOUR_USERNAME/agentnarna.git
cd agentnarna
chmod +x install.sh uninstall.sh
./install.sh --agent standalone
agentnarna setup
```

The installer adds `agentnarna` and the legacy `bughunter` alias. If
`~/.local/bin` is selected, follow the printed PATH instruction.

## How do I update it?

```bash
cd agentnarna
git pull --ff-only
./install.sh --agent standalone
```

## How do I remove it?

```bash
./uninstall.sh --agent standalone --yes
```

Add `--purge-config` only when you also want to remove the AgentNarna and legacy
saved provider configuration.

## Why are scanner results not immediately called findings?

Scanner labels, reflections, version matches, errors, and status-code changes
are leads. A finding needs a fresh deterministic oracle that reproduces real
impact. Each report receives evidence only from its own validated record.

## What happens after a 403, WAF page, or sanitizer?

The response is fingerprinted. AgentNarna chooses a different safe strategy
family—such as route normalization, method semantics, identity differential,
workflow order, alternate first-party surface, or browser oracle—without
repeating cosmetic payload variations. It stops when impact is proven, scope or
safety limits intervene, or distinct strategies are exhausted.

## Does it execute every generated command automatically?

No. Generated commands retain operator confirmation, scope checking, command
sanitization, and audit logging. Target-controlled text is treated as untrusted.

## How does online research work?

Medium and other sites can be consumed through RSS/Atom or explicit article
URLs. X recent search uses `X_BEARER_TOKEN`. Research is stored as compact,
source-linked, untrusted hypotheses and never becomes proof by popularity.

## Where is data stored?

The standalone CLI uses the checkout when it is writable, or
`~/.agentnarna` when installed read-only. Override the location with
`AGENTNARNA_HOME`. Hunt memory and evidence remain local unless the operator
explicitly exports them.

## Where should project security issues be reported?

Use GitHub private vulnerability reporting as described in
`.github/SECURITY.md`. Do not post exploit details for AgentNarna itself in a
public issue.
