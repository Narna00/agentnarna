"""Verified-only evidence collection for report generation.

Discovery artifacts are leads.  They never become report input merely because a
different finding in the same directory passed validation.  This module binds
each report section to the exact ``validation.json`` that promoted it and to
the evidence links declared by that validation record.
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Any

from tools.validate_core import is_report_ready


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def load_validations(findings_dir: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(ready, suppressed)`` validation records with source paths."""
    ready: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    pattern = os.path.join(findings_dir, "**", "validation.json")
    for name in sorted(glob.glob(pattern, recursive=True)):
        try:
            payload = json.loads(Path(name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            suppressed.append({"_path": name, "status": "invalid_validation"})
            continue
        payload["_path"] = name
        (ready if is_report_ready(payload) else suppressed).append(payload)
    return ready, suppressed


def _evidence_links(validation: dict[str, Any]) -> list[str]:
    finding = validation.get("finding") or {}
    links = validation.get("evidence_links") or finding.get("evidence_links") or []
    if isinstance(links, str):
        return [links]
    return [str(item) for item in links if isinstance(item, (str, os.PathLike))]


def _compact_validation(validation: dict[str, Any]) -> dict[str, Any]:
    """Keep proof-bearing fields and discard scanner summaries/drafts."""
    finding = validation.get("finding") or {}
    verifier = validation.get("verifier") or {}
    return {
        "finding_id": validation.get("finding_id"),
        "vulnerability_type": finding.get("vulnerability_type") or validation.get("vuln_class"),
        "program": finding.get("program"),
        "endpoint": finding.get("endpoint"),
        "impact": finding.get("impact"),
        "curl_poc": finding.get("curl_poc") or validation.get("curl_poc"),
        "cvss_score": finding.get("cvss_score"),
        "cvss_vector": finding.get("cvss_vector"),
        "verification_oracle": verifier.get("oracle"),
        "verification_evidence": verifier.get("evidence"),
        "verification_trace": verifier.get("trace") or [],
    }


def collect_verified_evidence(findings_dir: str, *, max_chars: int = 7000) -> str:
    """Build report context from report-ready validations only.

    Linked files are resolved relative to their own validation directory and
    must stay under ``findings_dir``.  Unlinked neighboring scanner output is
    intentionally invisible to the report writer.
    """
    root = Path(findings_dir).resolve()
    ready, _ = load_validations(findings_dir)
    sections: list[str] = []
    used = 0

    for idx, validation in enumerate(ready, 1):
        source = Path(validation["_path"])
        compact = json.dumps(_compact_validation(validation), indent=2, sort_keys=True)
        body = [f"## VERIFIED FINDING {idx}", f"Validation: {source.relative_to(root)}", compact]

        for link in _evidence_links(validation):
            candidate = (source.parent / link).resolve()
            if not _inside(candidate, root) or not candidate.is_file():
                continue
            try:
                content = candidate.read_text(encoding="utf-8", errors="replace")[:3000]
            except OSError:
                continue
            rel = candidate.relative_to(root)
            body.append(f"### Linked proof: {rel}\n{content}")

        section = "\n\n".join(body)
        remaining = max_chars - used
        if remaining <= 0:
            break
        sections.append(section[:remaining])
        used += min(len(section), remaining)

    return "\n\n".join(sections)


def report_gate_note(findings_dir: str) -> tuple[bool, str]:
    ready, suppressed = load_validations(findings_dir)
    if ready:
        return True, ""
    if not ready and not suppressed:
        return False, (
            "NO_REPORTS\nReport gate blocked: no validation.json found. Run the "
            "deterministic verifier first."
        )
    reasons = []
    for item in suppressed[:5]:
        source = os.path.basename(os.path.dirname(str(item.get("_path") or "unknown")))
        status = item.get("status") or "unverified"
        rejected = ", ".join(item.get("rejection_reasons") or []) or "unconfirmed"
        reasons.append(f"{source}: {status} ({rejected})")
    return False, (
        "NO_REPORTS\nReport gate blocked: no finding passed deterministic verification. "
        + "; ".join(reasons)
    )
