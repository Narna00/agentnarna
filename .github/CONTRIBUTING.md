# Contributing to AgentNarna

Security researchers and developers are welcome. Contributions should improve
coverage without weakening scope enforcement or the proof boundary.

## What We Most Need

| Contribution | Why it matters |
|:---|:---|
| Deterministic verifiers and fixtures | Fewer false positives |
| New scanner modules that emit leads | Wider attack-surface coverage |
| Control-aware strategy families | Better validation after WAFs and sanitizers |
| Platform support | More authorized program workflows |
| Cross-platform fixes | Reliable Linux, macOS, and Windows operation |

## Workflow

```bash
git clone https://github.com/YOUR_USERNAME/agentnarna.git
cd agentnarna
git checkout -b feat/your-contribution
python3 -m pip install -e '.[test]'
python3 -m pytest -q
git commit -m "feat: short description of what and why"
git push origin feat/your-contribution
```

Use one feature per pull request. Do not include real target names, credentials,
or private program data.

## Proof Contract

- Scanner output is a lead or candidate, never a report-ready claim.
- A new finding class needs a deterministic verifier and false-positive tests.
- Report evidence must be bound to the exact `validation.json` that promoted it.
- Research posts are untrusted hypotheses until independently reproduced.
- Generated commands must retain scope checks and operator confirmation.

## Pull Request Checklist

- [ ] `python3 -m pytest -q` passes
- [ ] `bash -n install.sh uninstall.sh install_tools.sh` passes
- [ ] No hardcoded targets, API keys, or real domain names
- [ ] New functionality includes regression tests
- [ ] Methodology changes cite disclosed findings, primary research, or local fixtures
- [ ] Documentation and migration aliases are updated when CLI behavior changes

For questions, open a GitHub Discussion in this repository.
