# Changelog

## 0.1.0 — AgentNarna foundation

### Added

- AgentNarna CLI, packaging metadata, Linux standalone installer, migration
  alias, and matching uninstaller.
- Per-finding verified evidence binding for report generation.
- Adaptive response fingerprinting and distinct validation strategy families.
- Medium/RSS, X recent-search, and explicit article intelligence ingestion.
- `adaptive-exploit-validation` and `research-intelligence` skills.
- Verified/suppressed state in the local Hunt Dashboard.
- Linux install/package smoke checks in GitHub Actions.
- Cross-platform file locking and process-group behavior.

### Changed

- Public UI, documentation, plugin metadata, and terminal banners now use the
  AgentNarna identity.
- Minimal artifact persistence is the default; audit mode remains opt-in.
- A lead must pass a deterministic verifier before becoming report input.
- WAF, 403, sanitizer, CSP, and rate-limit responses are treated as control
  fingerprints instead of final conclusions.

### Compatibility

- `bughunter` and selected `BBHUNT_*` / `BUGHUNTER_*` settings remain migration
  aliases. New installations should use `agentnarna`, `AGENTNARNA_HOME`, and
  `AGENTNARNA_ARTIFACT_MODE`.

The pre-fork project history remains available in Git history. Attribution and
the upstream MIT notice are preserved in `README.md` and `LICENSE`.
